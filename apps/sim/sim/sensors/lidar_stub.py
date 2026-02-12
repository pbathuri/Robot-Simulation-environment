"""Stub LiDAR: range array placeholder; optional noise."""

from typing import Any

from numpy.random import Generator

from apps.sim.sim.sensors.base import SensorModel


class LiDARStub(SensorModel):
    name = "lidar"

    def __init__(self, num_rays: int = 16, noise_scale: float = 0.0) -> None:
        self.num_rays = num_rays
        self.noise_scale = noise_scale

    def observe(
        self,
        state: dict[str, Any],
        t: float,
        *,
        rng: Generator | None = None,
    ) -> dict[str, Any]:
        x = state.get("x", 0.0)
        ranges = [float(x) + 1.0] * self.num_rays
        if rng is not None and self.noise_scale > 0:
            ranges = [r + float(rng.normal(0, self.noise_scale)) for r in ranges]
        return {"ranges": ranges, "num_rays": self.num_rays}
