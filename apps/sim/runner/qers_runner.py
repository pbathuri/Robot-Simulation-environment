"""
QERS runner: runs simulation with physics + Q-Plugin + sensors.
Produces telemetry + replay + metrics under runs/<run_id>/.
"""

import json
import logging
import math
import time
import uuid
from pathlib import Path
from typing import Any

from apps.sim.sim.core import SimCore
from apps.sim.sim.quantum.q_plugin import QPlugin
from apps.sim.sim.sensors.camera_stub import CameraStub
from apps.sim.sim.sensors.imu_stub import IMUStub
from apps.sim.sim.sensors.latency_wrapper import LatencyWrapper
from apps.sim.sim.residual.stub import StubResidualModel
from apps.sim.profiles.loader import load_profile

# Try PyBullet, fall back to stub
try:
    from apps.sim.sim.physics.pybullet_adapter import PyBulletAdapter
    USE_PYBULLET = True
except ImportError:
    USE_PYBULLET = False

logger = logging.getLogger(__name__)


def _generate_action(step_idx: int, num_joints: int, steps: int, seed: int) -> dict[str, Any]:
    """
    Generate a meaningful action sequence that moves the robot.
    Uses sinusoidal trajectories with varying frequency per joint
    so the sim produces real motion — not just zeros.
    """
    t = step_idx / max(steps, 1)
    targets = []
    for j in range(num_joints):
        freq = 0.5 + j * 0.3
        phase = j * 0.7 + seed * 0.01
        amplitude = 0.8 - j * 0.15
        targets.append(amplitude * math.sin(2 * math.pi * freq * t + phase))
    return {"joint_targets": targets}


def run_qers_sim(
    urdf_path: str,
    *,
    steps: int = 100,
    dt: float = 0.01,
    seed: int | None = None,
    use_q_plugin: bool = False,
    use_residual: bool = False,
    reality_profile: str | None = None,
    runs_dir: str | Path = "runs",
    run_id: str | None = None,
    _profile_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run simulation: physics + Q-Plugin + sensors. Returns run metadata."""
    run_id = run_id or str(uuid.uuid4())
    runs_path = Path(runs_dir)
    runs_path.mkdir(parents=True, exist_ok=True)
    run_dir = runs_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Resolve urdf_path relative to repo root
    urdf_path_obj = Path(urdf_path)
    if not urdf_path_obj.is_file():
        repo_root = Path(__file__).resolve().parents[2]
        alt = repo_root / urdf_path
        if alt.is_file():
            urdf_path = str(alt)

    logger.info(f"Starting run {run_id}", extra={"run_id": run_id, "urdf": urdf_path})
    seed = seed or 42

    # Load profile
    profile: dict[str, Any] = {}
    if _profile_override is not None:
        profile = _profile_override
    elif reality_profile:
        loaded = load_profile(reality_profile)
        if loaded:
            profile = loaded
        else:
            logger.warning(f"Profile '{reality_profile}' not found, using defaults")
    if not profile:
        profile = {
            "physics": {"gravity": [0, 0, -9.81], "friction": 0.5, "restitution": 0.0, "timestep": dt},
            "sensors": {"latency_steps": 0, "noise_scale": 0.01, "camera_degrade": False},
            "gap_knobs": {},
        }

    physics_cfg = profile.get("physics", {})
    sensors_cfg = profile.get("sensors", {})
    noise_scale = float(sensors_cfg.get("noise_scale", 0.01))
    latency_steps = int(sensors_cfg.get("latency_steps", 0))

    # Initialize physics
    if USE_PYBULLET and urdf_path:
        try:
            physics = PyBulletAdapter(urdf_path=urdf_path, timestep=dt, use_gui=False)
            physics.initialize()
        except Exception:
            logger.debug("PyBullet unavailable, using stub physics")
            from apps.sim.sim.physics.stub import StubPhysicsEngine
            physics = StubPhysicsEngine()
    else:
        from apps.sim.sim.physics.stub import StubPhysicsEngine
        physics = StubPhysicsEngine()

    # Sensors
    camera_degrade = bool(sensors_cfg.get("camera_degrade", False))
    cam = CameraStub(noise_scale=noise_scale, degrade=camera_degrade)
    imu = IMUStub(noise_scale=noise_scale)
    if latency_steps > 0:
        cam = LatencyWrapper(cam, latency_steps=latency_steps)
        imu = LatencyWrapper(imu, latency_steps=latency_steps)
    sensors = [cam, imu]

    # Q-Plugin
    q_plugin = QPlugin(use_quantum=use_q_plugin, noise_scale=noise_scale, seed=seed)

    # Residual
    residual_model = StubResidualModel() if use_residual else None

    # Core
    core = SimCore(
        physics, sensors, dt=dt, seed=seed,
        q_plugin=q_plugin, use_q_plugin=use_q_plugin,
        residual_model=residual_model if use_residual else None,
    )
    core.reset(seed=seed)

    # Get initial joint count
    initial_state = core.state
    num_joints = len(initial_state.get("joint_positions", []))

    # ── Simulation loop ──────────────────────────────────────────────────
    timeline: list[dict[str, Any]] = []
    actions_log: list[dict[str, Any]] = []
    step_times: list[float] = []

    for i in range(steps):
        t0 = time.time()

        # Generate meaningful action
        action = _generate_action(i, num_joints, steps, seed)

        # Step
        if use_q_plugin:
            step_out = core.step_quantum(action)
        elif use_residual and residual_model is not None:
            step_out = core.step_dr(action)
        else:
            step_out = core.step_stochastic(action)

        step_time = time.time() - t0
        step_times.append(step_time)
        actions_log.append(action)

        # Record full state for timeline
        state = step_out["state"]
        obs = step_out.get("observation", {})
        timeline.append({
            "step": i,
            "t": step_out["t"],
            "state": {
                "base_position": state.get("base_position", [0, 0, 0]),
                "joint_positions": state.get("joint_positions", []),
                "joint_velocities": state.get("joint_velocities", []),
                "link_positions": state.get("link_positions", []),
                "end_effector": state.get("end_effector", [0, 0, 0]),
            },
            "observation": {
                "imu_acc": obs.get("imu", {}).get("acc", 0),
                "camera_val": obs.get("camera", {}).get("placeholder_value", 0),
            },
            "action": action,
            "q_plugin_used": step_out.get("q_plugin_used", False),
            "step_time_ms": step_time * 1000,
        })

    # ── Metrics ──────────────────────────────────────────────────────────
    avg_step_time = sum(step_times) / len(step_times) if step_times else 0.0
    final_state = core.state
    ee = final_state.get("end_effector", [0, 0, 0])
    total_joint_travel = 0.0
    if len(timeline) > 1:
        for j in range(num_joints):
            for k in range(1, len(timeline)):
                jp_prev = timeline[k - 1]["state"]["joint_positions"]
                jp_curr = timeline[k]["state"]["joint_positions"]
                if j < len(jp_prev) and j < len(jp_curr):
                    total_joint_travel += abs(jp_curr[j] - jp_prev[j])

    metrics = {
        "run_id": run_id,
        "steps": steps,
        "dt": dt,
        "num_joints": num_joints,
        "avg_step_time_ms": avg_step_time * 1000,
        "total_time_s": sum(step_times),
        "q_plugin_used": use_q_plugin,
        "use_residual": use_residual,
        "reality_profile": reality_profile or "default",
        "end_effector_position": ee,
        "total_joint_travel_rad": round(total_joint_travel, 4),
        "physics_engine": "pybullet" if USE_PYBULLET else "stub",
    }
    with open(run_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Report (full timeline for charts)
    report = {
        "run_id": run_id,
        "config": {
            "urdf_path": urdf_path,
            "steps": steps,
            "dt": dt,
            "seed": seed,
            "use_q_plugin": use_q_plugin,
            "use_residual": use_residual,
            "reality_profile": reality_profile,
            "physics_config": physics_cfg,
            "sensors_config": sensors_cfg,
            "gap_knobs": profile.get("gap_knobs", {}),
            "integrator": "euler",
        },
        "metrics": metrics,
        "timeline": timeline,  # FULL timeline
    }
    with open(run_dir / "report.json", "w") as f:
        json.dump(report, f, indent=2)

    # Replay bundle
    replay = {
        "run_id": run_id,
        "config": report["config"],
        "seeds": {"main": seed},
        "initial_state": initial_state,
        "actions": actions_log,
    }
    with open(run_dir / "replay.json", "w") as f:
        json.dump(replay, f, indent=2)

    if hasattr(physics, "close"):
        physics.close()

    meta = {
        "run_id": run_id,
        "status": "completed",
        "run_dir": str(run_dir),
        "metrics": metrics,
    }
    logger.info(f"Run {run_id} completed")
    return meta
