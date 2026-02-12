"""Tests for domain randomization, batch runner, and eval metrics."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest


# ── Domain Randomization ────────────────────────────────────────────────────


def test_dr_config_from_default_profile() -> None:
    from apps.sim.sim.domain_randomization import DRConfig

    profile = {
        "physics": {"gravity": [0, 0, -9.81], "friction": 0.5, "restitution": 0.0},
        "sensors": {"latency_steps": 0, "noise_scale": 0.01},
        "gap_knobs": {"mass_scale": 1.0, "friction_range": [0.4, 0.6]},
    }
    config = DRConfig.from_profile(profile)
    assert config.friction_range == (0.4, 0.6)
    assert config.noise_scale_range[0] <= 0.01 <= config.noise_scale_range[1]


def test_dr_sampler_reproducibility() -> None:
    from apps.sim.sim.domain_randomization import DRConfig, DRSampler

    profile = {
        "physics": {"friction": 0.5},
        "sensors": {"noise_scale": 0.01},
        "gap_knobs": {"friction_range": [0.3, 0.7]},
    }
    config = DRConfig.from_profile(profile)
    s1 = DRSampler(config, seed=42)
    s2 = DRSampler(config, seed=42)
    r1 = s1.sample()
    r2 = s2.sample()
    assert r1.friction == r2.friction
    assert r1.noise_scale == r2.noise_scale


def test_dr_sampler_range_respected() -> None:
    from apps.sim.sim.domain_randomization import DRConfig, DRSampler

    config = DRConfig(friction_range=(0.1, 0.2), noise_scale_range=(0.01, 0.03))
    sampler = DRSampler(config, seed=0)
    for _ in range(50):
        r = sampler.sample()
        assert 0.1 <= r.friction <= 0.2
        assert 0.01 <= r.noise_scale <= 0.03


def test_dr_sample_n() -> None:
    from apps.sim.sim.domain_randomization import DRConfig, DRSampler

    config = DRConfig()
    sampler = DRSampler(config, seed=7)
    batch = sampler.sample_n(10)
    assert len(batch) == 10
    assert all(hasattr(r, "friction") for r in batch)


# ── SimCore DR step ─────────────────────────────────────────────────────────


def test_step_dr_basic() -> None:
    from apps.sim.sim.core import SimCore
    from apps.sim.sim.physics.stub import StubPhysicsEngine
    from apps.sim.sim.sensors.imu_stub import IMUStub

    physics = StubPhysicsEngine()
    sensors = [IMUStub(noise_scale=0.1)]
    core = SimCore(physics, sensors, dt=0.01, seed=42)
    core.reset(state={"x": 0.0, "v": 0.0}, seed=42)
    core.apply_dr(noise_scale=0.05, action_noise_scale=0.01)

    out = core.step_dr({"v": 1.0})
    assert "state" in out
    assert "action_noisy" in out
    assert "residual_delta" in out
    assert out["t"] > 0


def test_step_dr_with_residual() -> None:
    from apps.sim.sim.core import SimCore
    from apps.sim.sim.physics.stub import StubPhysicsEngine
    from apps.sim.sim.sensors.imu_stub import IMUStub
    from apps.sim.sim.residual.stub import StubResidualModel

    physics = StubPhysicsEngine()
    sensors = [IMUStub(noise_scale=0.0)]
    residual = StubResidualModel()
    core = SimCore(physics, sensors, dt=0.01, seed=42, residual_model=residual)
    core.reset(state={"x": 0.0, "v": 0.0}, seed=42)
    out = core.step_dr({"v": 0.5})
    assert out["state"]["x"] is not None  # Stub returns zero delta


# ── Batch Runner ────────────────────────────────────────────────────────────


def test_batch_runner_single_profile() -> None:
    from apps.sim.runner.batch_runner import run_batch

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_batch(
            "examples/simple_robot.urdf",
            profiles=["default"],
            steps=10,
            dt=0.01,
            seed=42,
            dr_episodes_per_profile=2,
            runs_dir=tmpdir,
        )
        assert "batch_id" in report
        assert len(report["per_profile"]) == 1
        assert report["per_profile"][0]["profile_id"] == "default"
        assert report["per_profile"][0]["summary"]["total_episodes"] == 2
        assert report["per_profile"][0]["summary"]["completed"] >= 1

        # Check batch report file written
        batch_dir = Path(tmpdir) / report["batch_id"]
        assert (batch_dir / "batch_report.json").is_file()


def test_batch_runner_multi_profile() -> None:
    from apps.sim.runner.batch_runner import run_batch

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_batch(
            "examples/simple_robot.urdf",
            profiles=["default", "slippery_warehouse"],
            steps=10,
            dt=0.01,
            seed=42,
            dr_episodes_per_profile=1,
            runs_dir=tmpdir,
        )
        assert len(report["per_profile"]) == 2
        pids = [p["profile_id"] for p in report["per_profile"]]
        assert "default" in pids
        assert "slippery_warehouse" in pids


# ── Eval Metrics ────────────────────────────────────────────────────────────


def test_performance_drop_computation() -> None:
    from apps.sim.eval.batch_eval import compute_performance_drop

    design = {"avg_step_time_ms": 0.05}
    eval_ = {"avg_step_time_ms": 0.08}
    result = compute_performance_drop(design, eval_, metric_key="avg_step_time_ms")
    assert result["absolute_drop"] == pytest.approx(0.03, abs=1e-6)
    assert result["relative_drop"] == pytest.approx(0.6, abs=1e-6)


def test_gap_width_computation() -> None:
    from apps.sim.eval.batch_eval import compute_gap_width

    prof_a = {"physics": {"friction": 0.5, "restitution": 0.0, "gravity": [0, 0, -9.81]},
              "sensors": {"noise_scale": 0.01, "latency_steps": 0}}
    prof_b = {"physics": {"friction": 0.3, "restitution": 0.1, "gravity": [0, 0, -9.71]},
              "sensors": {"noise_scale": 0.05, "latency_steps": 3}}
    result = compute_gap_width(prof_a, prof_b)
    assert result["l1_distance"] > 0
    assert result["l2_distance"] > 0
    assert 0 <= result["cosine_similarity"] <= 1


def test_rank_stability_no_inversion() -> None:
    from apps.sim.eval.batch_eval import compute_rank_stability

    results = {
        "method_A": [
            {"profile_id": "default", "metrics": {"avg_step_time_ms": 0.05}},
            {"profile_id": "slippery", "metrics": {"avg_step_time_ms": 0.06}},
        ],
        "method_B": [
            {"profile_id": "default", "metrics": {"avg_step_time_ms": 0.10}},
            {"profile_id": "slippery", "metrics": {"avg_step_time_ms": 0.12}},
        ],
    }
    result = compute_rank_stability(results, metric_key="avg_step_time_ms", lower_is_better=True)
    assert result["is_stable"] is True
    assert result["rank_inversions"] == 0


def test_rank_stability_with_inversion() -> None:
    from apps.sim.eval.batch_eval import compute_rank_stability

    results = {
        "method_A": [
            {"profile_id": "default", "metrics": {"avg_step_time_ms": 0.05}},
            {"profile_id": "slippery", "metrics": {"avg_step_time_ms": 0.15}},
        ],
        "method_B": [
            {"profile_id": "default", "metrics": {"avg_step_time_ms": 0.10}},
            {"profile_id": "slippery", "metrics": {"avg_step_time_ms": 0.06}},
        ],
    }
    result = compute_rank_stability(results, metric_key="avg_step_time_ms", lower_is_better=True)
    assert result["is_stable"] is False
    assert result["rank_inversions"] >= 1


# ── Learned Residual Model ──────────────────────────────────────────────────


def test_learned_residual_zero_when_no_weights() -> None:
    from apps.sim.sim.residual.learned import LearnedResidualModel

    model = LearnedResidualModel(weights=None)
    delta = model.predict_delta({"x": 1.0, "v": 0.5}, {"v": 0.1}, {})
    assert delta == {}  # No joint_positions key


def test_learned_residual_with_random_weights() -> None:
    from apps.sim.sim.residual.learned import LearnedResidualModel

    weights = LearnedResidualModel.create_random_weights(state_dim=2, action_dim=1, hidden_dim=16, seed=0)
    model = LearnedResidualModel(weights=weights, state_keys=["x", "v"], action_keys=["v"])
    delta = model.predict_delta({"x": 1.0, "v": 0.5}, {"v": 0.1}, {})
    assert "x" in delta
    assert "v" in delta
    # Scale near zero because of small weight init
    assert abs(delta["x"]) < 0.1
    assert abs(delta["v"]) < 0.1
