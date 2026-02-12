"""Tests for sim core: determinism and step interface."""

import numpy as np

import pytest


def test_step_deterministic() -> None:
    from apps.sim.sim.core import SimCore
    from apps.sim.sim.physics.stub import StubPhysicsEngine
    from apps.sim.sim.sensors.imu_stub import IMUStub

    physics = StubPhysicsEngine()
    sensors = [IMUStub(noise_scale=0.0)]
    core = SimCore(physics, sensors, dt=0.01, seed=42)
    initial = {"x": 0.0, "v": 0.0}
    core.reset(state=initial, seed=42)
    out1 = core.step({"v": 0.1})
    core.reset(state=initial, seed=42)
    out2 = core.step({"v": 0.1})
    assert out1["state"] == out2["state"]
    assert out1["observation"] == out2["observation"]


def test_stochastic_reproducible_with_seed() -> None:
    from apps.sim.sim.core import SimCore
    from apps.sim.sim.physics.stub import StubPhysicsEngine
    from apps.sim.sim.sensors.imu_stub import IMUStub

    physics = StubPhysicsEngine()
    sensors = [IMUStub(noise_scale=0.5)]
    core = SimCore(physics, sensors, dt=0.01, seed=123)
    initial = {"x": 0.0, "v": 0.0}
    core.reset(state=initial, seed=123)
    out1 = core.step_stochastic({"v": 0.1})
    core.reset(state=initial, seed=123)
    out2 = core.step_stochastic({"v": 0.1})
    assert out1["state"] == out2["state"]
    assert out1["observation"] == out2["observation"]
