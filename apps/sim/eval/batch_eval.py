"""
Batch evaluation metrics for multi-profile / pseudo-reality experiments.

Implements:
  - replay_error: replay actions from profile A in profile B, measure trajectory divergence
  - performance_drop: metric delta between design profile and evaluation profiles
  - rank_stability: whether method/config ranking is preserved across profiles
  - gap_width: L1/L2/cosine distance between profile parameter vectors (Ligot & Birattari 2019)

All outputs conform to JSON-serializable dicts.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def compute_replay_error(
    design_replay_path: str | Path,
    eval_run_dir: str | Path,
) -> dict[str, Any]:
    """
    Replay actions from a design-profile run inside an evaluation-profile run directory.
    Compare resulting state trajectories step-by-step.

    Returns:
        {
            "mean_position_error": float,
            "max_position_error": float,
            "mean_velocity_error": float,
            "num_steps_compared": int,
        }
    """
    design_replay = _load_json(design_replay_path)
    eval_replay = _load_json(Path(eval_run_dir) / "replay.json")

    if design_replay is None or eval_replay is None:
        return {"error": "Replay file(s) not found", "mean_position_error": None}

    d_actions = design_replay.get("actions", [])
    e_actions = eval_replay.get("actions", [])

    # Compare trajectories using the report timelines or replay states
    # For now, compute error from logged state summaries in reports
    design_report = _load_json(Path(design_replay_path).parent / "report.json")
    eval_report = _load_json(Path(eval_run_dir) / "report.json")

    if design_report is None or eval_report is None:
        return {"error": "Report file(s) not found", "mean_position_error": None}

    d_timeline = design_report.get("timeline_summary", [])
    e_timeline = eval_report.get("timeline_summary", [])

    n = min(len(d_timeline), len(e_timeline))
    if n == 0:
        return {"mean_position_error": 0.0, "max_position_error": 0.0, "num_steps_compared": 0}

    pos_errors = []
    for i in range(n):
        d_state = d_timeline[i].get("state", d_timeline[i].get("state_summary", {}))
        e_state = e_timeline[i].get("state", e_timeline[i].get("state_summary", {}))
        d_pos = d_state.get("end_effector", d_state.get("base_position", d_state.get("base_pos", [0.0, 0.0])))
        e_pos = e_state.get("end_effector", e_state.get("base_position", e_state.get("base_pos", [0.0, 0.0])))
        err = math.sqrt(sum((a - b) ** 2 for a, b in zip(d_pos, e_pos)))
        pos_errors.append(err)

    return {
        "mean_position_error": sum(pos_errors) / len(pos_errors),
        "max_position_error": max(pos_errors),
        "num_steps_compared": n,
    }


def compute_performance_drop(
    design_metrics: dict[str, Any],
    eval_metrics: dict[str, Any],
    *,
    metric_key: str = "avg_step_time_ms",
) -> dict[str, Any]:
    """
    Compute performance drop between design-profile and evaluation-profile metrics.

    A positive drop means performance degraded in the evaluation profile.
    For metrics where *lower* is better (e.g. step time), drop = eval - design.
    For metrics where *higher* is better (e.g. reward), drop = design - eval.
    """
    d_val = design_metrics.get(metric_key)
    e_val = eval_metrics.get(metric_key)

    if d_val is None or e_val is None:
        return {"metric_key": metric_key, "drop": None, "design_value": d_val, "eval_value": e_val}

    # Default: assume lower is better (step time, error)
    drop = float(e_val) - float(d_val)
    relative_drop = drop / float(d_val) if d_val != 0 else None

    return {
        "metric_key": metric_key,
        "design_value": float(d_val),
        "eval_value": float(e_val),
        "absolute_drop": drop,
        "relative_drop": relative_drop,
    }


def compute_rank_stability(
    results_by_method: dict[str, list[dict[str, Any]]],
    *,
    metric_key: str = "avg_step_time_ms",
    lower_is_better: bool = True,
) -> dict[str, Any]:
    """
    Check whether the ranking of methods/configs is preserved across profiles.

    Args:
        results_by_method: {method_name: [{profile_id, metrics}, ...]}
        metric_key: which metric to rank on
        lower_is_better: sort direction

    Returns:
        {
            "per_profile_rankings": {profile_id: [ranked methods]},
            "rank_inversions": int,  # number of profile pairs where ranking flips
            "is_stable": bool,
        }

    Follows Ligot & Birattari: a rank inversion means method A beats B in one profile
    but B beats A in another.
    """
    methods = list(results_by_method.keys())
    if len(methods) < 2:
        return {"per_profile_rankings": {}, "rank_inversions": 0, "is_stable": True}

    # Collect per-profile values per method
    profile_ids: set[str] = set()
    for method_results in results_by_method.values():
        for r in method_results:
            profile_ids.add(r.get("profile_id", ""))

    per_profile_rankings: dict[str, list[str]] = {}
    method_scores: dict[str, dict[str, float]] = {m: {} for m in methods}

    for method, results in results_by_method.items():
        for r in results:
            pid = r.get("profile_id", "")
            val = r.get("metrics", {}).get(metric_key)
            if val is not None:
                method_scores[method][pid] = float(val)

    for pid in profile_ids:
        scores = []
        for m in methods:
            v = method_scores[m].get(pid)
            if v is not None:
                scores.append((m, v))
        scores.sort(key=lambda x: x[1], reverse=not lower_is_better)
        per_profile_rankings[pid] = [s[0] for s in scores]

    # Count inversions: for each pair of profiles, check if top method flips
    inversions = 0
    pid_list = list(per_profile_rankings.keys())
    for i in range(len(pid_list)):
        for j in range(i + 1, len(pid_list)):
            r1 = per_profile_rankings[pid_list[i]]
            r2 = per_profile_rankings[pid_list[j]]
            if len(r1) >= 2 and len(r2) >= 2 and r1[0] != r2[0]:
                inversions += 1

    return {
        "per_profile_rankings": per_profile_rankings,
        "rank_inversions": inversions,
        "is_stable": inversions == 0,
    }


def compute_gap_width(
    profile_a: dict[str, Any],
    profile_b: dict[str, Any],
) -> dict[str, Any]:
    """
    Compute the "width" of the artificial reality gap between two profiles.
    Uses parameter vectors from physics + sensors configs (Ligot & Birattari 2019).

    Returns L1, L2, cosine distance metrics.
    """
    vec_a = _profile_to_vector(profile_a)
    vec_b = _profile_to_vector(profile_b)

    if len(vec_a) != len(vec_b):
        return {"error": "Parameter vector length mismatch"}

    diff = [b - a for a, b in zip(vec_a, vec_b)]
    l1 = sum(abs(d) for d in diff)
    l2 = math.sqrt(sum(d ** 2 for d in diff))

    # Cosine similarity
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a ** 2 for a in vec_a))
    mag_b = math.sqrt(sum(b ** 2 for b in vec_b))
    cosine_sim = dot / (mag_a * mag_b) if (mag_a * mag_b) > 0 else 0.0

    return {
        "l1_distance": l1,
        "l2_distance": l2,
        "cosine_similarity": cosine_sim,
        "cosine_distance": 1.0 - cosine_sim,
        "param_diff": diff,
        "vec_a": vec_a,
        "vec_b": vec_b,
    }


def _profile_to_vector(profile: dict[str, Any]) -> list[float]:
    """
    Convert a profile to a flat parameter vector:
    [friction, restitution, gravity_z, noise_scale, latency_steps]
    Matches Ligot & Birattari's 5D parameter space.
    """
    physics = profile.get("physics", {})
    sensors = profile.get("sensors", {})
    return [
        float(physics.get("friction", 0.5)),
        float(physics.get("restitution", 0.0)),
        float(physics.get("gravity", [0, 0, -9.81])[2]),
        float(sensors.get("noise_scale", 0.01)),
        float(sensors.get("latency_steps", 0)),
    ]


def evaluate_batch_report(batch_report: dict[str, Any]) -> dict[str, Any]:
    """
    Given a batch report (from batch_runner), compute cross-profile evaluation metrics.

    Returns:
        {
            "pairwise_drops": [...],
            "gap_widths": [...],
            "summary": {mean_drop, max_drop, profiles_evaluated}
        }
    """
    from apps.sim.profiles.loader import load_profile

    per_profile = batch_report.get("per_profile", [])
    profiles_config = batch_report.get("config", {}).get("profiles", [])

    # Load profile configs for gap width computation
    profile_configs: dict[str, dict[str, Any]] = {}
    for pid in profiles_config:
        cfg = load_profile(pid)
        if cfg:
            profile_configs[pid] = cfg

    # Compute pairwise performance drops
    pairwise_drops: list[dict[str, Any]] = []
    for i, pp_a in enumerate(per_profile):
        for j, pp_b in enumerate(per_profile):
            if i >= j:
                continue
            pid_a = pp_a["profile_id"]
            pid_b = pp_b["profile_id"]

            metrics_a = pp_a["summary"]
            metrics_b = pp_b["summary"]
            drop = compute_performance_drop(metrics_a, metrics_b, metric_key="avg_step_time_ms")

            # Gap width
            gap = {}
            if pid_a in profile_configs and pid_b in profile_configs:
                gap = compute_gap_width(profile_configs[pid_a], profile_configs[pid_b])

            pairwise_drops.append({
                "design_profile": pid_a,
                "eval_profile": pid_b,
                "performance_drop": drop,
                "gap_width": gap,
            })

    drops = [pd["performance_drop"].get("absolute_drop", 0) for pd in pairwise_drops
             if pd["performance_drop"].get("absolute_drop") is not None]

    return {
        "pairwise_drops": pairwise_drops,
        "summary": {
            "profiles_evaluated": len(per_profile),
            "pairwise_comparisons": len(pairwise_drops),
            "mean_absolute_drop": sum(abs(d) for d in drops) / len(drops) if drops else 0.0,
            "max_absolute_drop": max(abs(d) for d in drops) if drops else 0.0,
        },
    }


def _load_json(path: Path | str) -> dict[str, Any] | None:
    p = Path(path)
    if not p.is_file():
        return None
    with open(p) as f:
        return json.load(f)
