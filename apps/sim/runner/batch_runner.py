"""
Batch runner: run the same scenario across multiple reality profiles.

Implements the "pseudo-reality evaluation" concept (Ligot & Birattari 2019):
- Design a controller/config on one profile ("design model")
- Evaluate on N other profiles ("pseudo-realities")
- Compare metrics: performance drop, rank stability

Also supports DR-sampled batches: run N episodes with DRSampler-drawn params
from a single profile to assess expected performance variance.

Output:  runs/<batch_id>/batch_report.json
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from apps.sim.profiles.loader import load_profile, list_profiles
from apps.sim.runner.qers_runner import run_qers_sim
from apps.sim.sim.domain_randomization import DRConfig, DRSampler

logger = logging.getLogger(__name__)


def run_batch(
    urdf_path: str,
    *,
    profiles: list[str] | None = None,
    steps: int = 100,
    dt: float = 0.01,
    seed: int = 42,
    use_q_plugin: bool = False,
    use_residual: bool = False,
    dr_episodes_per_profile: int = 1,
    runs_dir: str | Path = "runs",
    batch_id: str | None = None,
) -> dict[str, Any]:
    """
    Run sim across multiple reality profiles and/or DR episodes.

    Args:
        profiles: list of profile IDs. If None, uses all available profiles.
        dr_episodes_per_profile: how many DR-sampled episodes per profile (≥1).
        batch_id: optional batch ID; auto-generated if not provided.

    Returns:
        batch_report dict with per-profile results and cross-profile stats.
    """
    batch_id = batch_id or f"batch_{uuid.uuid4().hex[:12]}"
    runs_path = Path(runs_dir)
    batch_dir = runs_path / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    # Resolve profiles
    if profiles is None or len(profiles) == 0:
        profiles = [p["id"] for p in list_profiles()]
    if not profiles:
        profiles = ["default"]

    logger.info("Batch %s: %d profiles, %d DR episodes each", batch_id, len(profiles), dr_episodes_per_profile)

    t0 = time.time()
    per_profile_results: list[dict[str, Any]] = []

    for profile_id in profiles:
        profile_data = load_profile(profile_id) or {}
        dr_config = DRConfig.from_profile(profile_data)
        dr_sampler = DRSampler(dr_config, seed=seed)

        episode_results: list[dict[str, Any]] = []

        for ep in range(dr_episodes_per_profile):
            dr_realization = dr_sampler.sample()
            ep_seed = seed + ep  # Vary seed per episode for different trajectories

            # Build a per-episode profile override using DR realization
            ep_profile = _overlay_dr(profile_data, dr_realization)

            run_id = f"{batch_id}__{profile_id}__ep{ep}"
            try:
                meta = run_qers_sim(
                    urdf_path,
                    steps=steps,
                    dt=dt,
                    seed=ep_seed,
                    use_q_plugin=use_q_plugin,
                    use_residual=use_residual,
                    reality_profile=None,  # We pass params directly below
                    runs_dir=str(runs_path),
                    run_id=run_id,
                    _profile_override=ep_profile,
                )
                episode_results.append({
                    "run_id": run_id,
                    "episode": ep,
                    "dr_realization": dr_realization.to_dict() if hasattr(dr_realization, "to_dict") else {},
                    "metrics": meta.get("metrics", {}),
                    "status": "completed",
                })
            except Exception as exc:
                logger.error("Batch %s profile %s ep %d failed: %s", batch_id, profile_id, ep, exc)
                episode_results.append({
                    "run_id": run_id,
                    "episode": ep,
                    "dr_realization": dr_realization.to_dict() if hasattr(dr_realization, "to_dict") else {},
                    "metrics": {},
                    "status": "failed",
                    "error": str(exc),
                })

        # Aggregate per-profile
        completed = [e for e in episode_results if e["status"] == "completed"]
        avg_step_time = _safe_mean([e["metrics"].get("avg_step_time_ms", 0) for e in completed])
        total_time = sum(e["metrics"].get("total_time_s", 0) for e in completed)

        per_profile_results.append({
            "profile_id": profile_id,
            "episodes": episode_results,
            "summary": {
                "total_episodes": dr_episodes_per_profile,
                "completed": len(completed),
                "failed": dr_episodes_per_profile - len(completed),
                "avg_step_time_ms": avg_step_time,
                "total_time_s": total_time,
            },
        })

    # Cross-profile stats
    total_time = time.time() - t0
    cross_profile = _compute_cross_profile_stats(per_profile_results)

    batch_report = {
        "batch_id": batch_id,
        "config": {
            "urdf_path": urdf_path,
            "profiles": profiles,
            "steps": steps,
            "dt": dt,
            "seed": seed,
            "use_q_plugin": use_q_plugin,
            "use_residual": use_residual,
            "dr_episodes_per_profile": dr_episodes_per_profile,
        },
        "per_profile": per_profile_results,
        "cross_profile": cross_profile,
        "total_time_s": total_time,
    }

    # Write report
    report_path = batch_dir / "batch_report.json"
    with open(report_path, "w") as f:
        json.dump(batch_report, f, indent=2)

    logger.info("Batch %s completed in %.1fs. Report: %s", batch_id, total_time, report_path)
    return batch_report


def _overlay_dr(profile_data: dict[str, Any], dr_realization: Any) -> dict[str, Any]:
    """
    Create an episode-specific profile by overlaying DR realization onto base profile.
    Returns a profile dict with concrete physics/sensor values.
    """
    p = dict(profile_data)
    physics = dict(p.get("physics", {}))
    sensors = dict(p.get("sensors", {}))

    # Overlay DR-drawn values
    physics["friction"] = dr_realization.friction
    physics["restitution"] = dr_realization.restitution
    grav = list(physics.get("gravity", [0, 0, -9.81]))
    grav[2] = dr_realization.gravity_z
    physics["gravity"] = grav

    sensors["noise_scale"] = dr_realization.noise_scale
    sensors["latency_steps"] = dr_realization.latency_steps
    sensors["camera_degrade"] = dr_realization.camera_degrade

    p["physics"] = physics
    p["sensors"] = sensors
    # Preserve gap_knobs for logging but mark as "realized"
    p["dr_realization"] = dr_realization.to_dict() if hasattr(dr_realization, "to_dict") else {}
    return p


def _compute_cross_profile_stats(per_profile: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute cross-profile comparison: step-time spread, performance consistency."""
    step_times = []
    for pp in per_profile:
        st = pp["summary"].get("avg_step_time_ms")
        if st is not None and st > 0:
            step_times.append(st)

    return {
        "num_profiles": len(per_profile),
        "step_time_mean_ms": _safe_mean(step_times),
        "step_time_std_ms": _safe_std(step_times),
        "step_time_min_ms": min(step_times) if step_times else 0.0,
        "step_time_max_ms": max(step_times) if step_times else 0.0,
    }


def _safe_mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _safe_std(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _safe_mean(vals)
    return (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5
