"""Stub IMU: linear/angular placeholder; optional noise."""

from typing import Any

from numpy.random import Generator

from apps.sim.sim.sensors.base import SensorModel


class IMUStub(SensorModel):
    name = "imu"

    def __init__(self, noise_scale: float = 0.0) -> None:
        self.noise_scale = noise_scale

    def observe(
        self,
        state: dict[str, Any],
        t: float,
        *,
        rng: Generator | None = None,
    ) -> dict[str, Any]:
        v = state.get("v", 0.0)
        acc = 0.0
        gyro = [0.0, 0.0, 0.0]
        if rng is not None and self.noise_scale > 0:
            acc += float(rng.normal(0, self.noise_scale))
        return {"acc": acc, "gyro": gyro, "vel_estimate": v}
