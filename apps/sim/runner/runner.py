"""
Scenario runner: single run and batch (multiprocessing placeholder).
Produces telemetry + replay bundle under runs/<run_id>/.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from apps.sim.contracts.replay import ReplayBundle
from apps.sim.contracts.run import RunStatus
from apps.sim.sim.core import SimCore
from apps.sim.sim.physics.stub import StubPhysicsEngine
from apps.sim.sim.sensors.camera_stub import CameraStub
from apps.sim.sim.sensors.imu_stub import IMUStub
from apps.sim.sim.sensors.lidar_stub import LiDARStub

logger = logging.getLogger(__name__)

# OpenTelemetry-friendly: structured fields
RUN_ID_KEY = "run_id"
SCENARIO_KEY = "scenario"
SEED_KEY = "seed"


def _default_sim_config() -> dict[str, Any]:
    return {
        "dt": 0.01,
        "steps": 50,
        "seed": 42,
        "stochastic": False,
    }


def run_scenario(
    scenario: str = "default",
    config: dict[str, Any] | None = None,
    run_id: str | None = None,
    runs_dir: str | Path = "runs",
) -> dict[str, Any]:
    """
    Run a single scenario: build sim, step N times, write telemetry + replay to runs/<run_id>/.
    Returns run metadata (run_id, status, path, metrics_summary).
    """
    cfg = _default_sim_config()
    if config:
        cfg.update(config)
    run_id = run_id or str(uuid.uuid4())
    runs_path = Path(runs_dir)
    runs_path.mkdir(parents=True, exist_ok=True)
    run_dir = runs_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Starting run",
        extra={RUN_ID_KEY: run_id, SCENARIO_KEY: scenario, SEED_KEY: cfg.get("seed")},
    )

    seed = cfg.get("seed", 42)
    physics = StubPhysicsEngine()
    sensors = [CameraStub(noise_scale=0.01), LiDARStub(16, 0.01), IMUStub(0.01)]
    core = SimCore(physics, sensors, dt=cfg["dt"], seed=seed)
    core.reset(seed=seed)

    steps = int(cfg["steps"])
    stochastic = cfg.get("stochastic", False)
    actions_log: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []

    for i in range(steps):
        action = {"v": 0.1}  # constant velocity for demo
        if stochastic:
            step_out = core.step_stochastic(action)
        else:
            step_out = core.step(action)
        actions_log.append(step_out["action"])
        timeline.append({
            "t": step_out["t"],
            "state": step_out["state"],
            "observation_keys": list(step_out["observation"].keys()),
        })

    # Replay bundle
    replay = ReplayBundle(
        run_id=run_id,
        config=cfg,
        seeds={"main": seed},
        initial_state=core.state,
        actions=actions_log,
    )
    replay_path = run_dir / "replay.json"
    with open(replay_path, "w") as f:
        json.dump(replay.model_dump(), f, indent=2)

    # Telemetry summary (OpenTelemetry-friendly schema: timestamp, severity, fields)
    telemetry_path = run_dir / "telemetry.json"
    with open(telemetry_path, "w") as f:
        json.dump({
            "run_id": run_id,
            "scenario": scenario,
            "config_snapshot": cfg,
            "seeds": {"main": seed},
            "steps": steps,
            "timeline_events": timeline[:5],  # first 5 for size; full in replay
        }, f, indent=2)

    # Metadata for API/dashboard
    meta = {
        "run_id": run_id,
        "status": RunStatus.COMPLETED.value,
        "scenario": scenario,
        "config_snapshot": cfg,
        "seeds": {"main": seed},
        "metrics_summary": {"cumulative_reward": None, "task_success_rate": None},
        "run_dir": str(run_dir),
    }
    meta_path = run_dir / "meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    logger.info("Run completed", extra={RUN_ID_KEY: run_id})
    return meta


def run_scenario_batch(
    scenario: str,
    n: int,
    configs: list[dict[str, Any]] | None = None,
    runs_dir: str | Path = "runs",
    parallel: bool = False,
) -> list[dict[str, Any]]:
    """
    Run n scenarios. If configs is provided, len(configs) must be n.
    parallel=True: use multiprocessing (placeholder: still sequential for now).
    """
    if configs is not None and len(configs) != n:
        raise ValueError("len(configs) must equal n")
    results: list[dict[str, Any]] = []
    for i in range(n):
        cfg = configs[i] if configs else None
        if cfg is None:
            cfg = {"seed": 42 + i}
        meta = run_scenario(scenario=scenario, config=cfg, runs_dir=runs_dir)
        results.append(meta)
    return results
