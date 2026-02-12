"""Stub camera: returns state-derived 'image' placeholder; optional noise."""

from typing import Any

from numpy.random import Generator

from apps.sim.sim.sensors.base import SensorModel


class CameraStub(SensorModel):
    name = "camera"

    def __init__(self, noise_scale: float = 0.0, degrade: bool = False) -> None:
        self.noise_scale = noise_scale
        self.degrade = degrade  # Extra noise/blur for sim-to-real "degrade" option

    def observe(
        self,
        state: dict[str, Any],
        t: float,
        *,
        rng: Generator | None = None,
    ) -> dict[str, Any]:
        # Placeholder: "image" as a tiny array derived from state
        x = state.get("x", 0.0)
        val = float(x) + t * 0.01
        if rng is not None and self.noise_scale > 0:
            val += float(rng.normal(0, self.noise_scale))
        if self.degrade and rng is not None:
            # Degrade: extra multiplicative noise (blur/artifact proxy)
            val *= 1.0 + float(rng.uniform(-0.1, 0.1))
        return {"shape": [32, 32], "placeholder_value": val, "degraded": self.degrade}
