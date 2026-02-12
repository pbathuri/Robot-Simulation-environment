"""
Domain Randomization: sample concrete physics/sensor params from gap_knobs ranges.

Each episode, DRSampler draws a realization of the randomizable parameters
(mass_scale, friction, restitution, sensor noise, latency, gravity perturbation, etc.)
so that training and evaluation expose the policy to a range of "pseudo-realities"
(cf. Ligot & Birattari 2019; Scheuch 2025 survey).

Usage:
    config = DRConfig.from_profile(profile_dict)
    sampler = DRSampler(config, seed=42)
    concrete = sampler.sample()
    # concrete.friction -> float drawn from config.friction_range
"""

from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np
from numpy.random import Generator


@dataclasses.dataclass(frozen=True)
class DRConfig:
    """Ranges for domain-randomizable parameters.  Built from a reality profile's gap_knobs."""

    # Physics
    mass_scale_range: tuple[float, float] = (1.0, 1.0)
    friction_range: tuple[float, float] = (0.4, 0.6)
    restitution_range: tuple[float, float] = (0.0, 0.0)
    gravity_z_range: tuple[float, float] = (-9.81, -9.81)

    # Sensors
    noise_scale_range: tuple[float, float] = (0.005, 0.02)
    latency_steps_range: tuple[int, int] = (0, 0)
    camera_degrade_prob: float = 0.0  # probability that camera is degraded

    # Actuation
    action_delay_range: tuple[int, int] = (0, 0)
    action_noise_scale_range: tuple[float, float] = (0.0, 0.0)

    @classmethod
    def from_profile(cls, profile: dict[str, Any]) -> DRConfig:
        """Build DR config from a reality profile dict (physics + sensors + gap_knobs)."""
        physics = profile.get("physics", {})
        sensors = profile.get("sensors", {})
        knobs = profile.get("gap_knobs", {})

        # Friction: explicit range in gap_knobs, or ±10% of physics.friction
        friction_base = float(physics.get("friction", 0.5))
        friction_range = tuple(knobs.get("friction_range", [friction_base * 0.9, friction_base * 1.1]))

        # Mass scale
        ms = knobs.get("mass_scale", 1.0)
        if isinstance(ms, (list, tuple)) and len(ms) == 2:
            mass_scale_range = tuple(ms)
        else:
            mass_scale_range = (float(ms) * 0.95, float(ms) * 1.05)

        # Restitution
        rest_base = float(physics.get("restitution", 0.0))
        rest_range = tuple(knobs.get("restitution_range", [max(0.0, rest_base - 0.05), rest_base + 0.05]))

        # Gravity
        grav_z = float(physics.get("gravity", [0, 0, -9.81])[2])
        grav_range = tuple(knobs.get("gravity_z_range", [grav_z - 0.1, grav_z + 0.1]))

        # Noise
        noise_base = float(sensors.get("noise_scale", 0.01))
        noise_range = tuple(knobs.get("noise_scale_range", [noise_base * 0.5, noise_base * 2.0]))

        # Latency
        lat_base = int(sensors.get("latency_steps", 0))
        lat_range = tuple(knobs.get("latency_steps_range", [max(0, lat_base - 1), lat_base + 2]))

        # Camera degrade
        cam_deg_prob = float(knobs.get("camera_degrade_prob", 0.0))

        # Actuation
        act_delay_range = tuple(knobs.get("action_delay_range", [0, 0]))
        act_noise_range = tuple(knobs.get("action_noise_scale_range", [0.0, 0.0]))

        return cls(
            mass_scale_range=mass_scale_range,
            friction_range=friction_range,
            restitution_range=rest_range,
            gravity_z_range=grav_range,
            noise_scale_range=noise_range,
            latency_steps_range=lat_range,
            camera_degrade_prob=cam_deg_prob,
            action_delay_range=act_delay_range,
            action_noise_scale_range=act_noise_range,
        )


@dataclasses.dataclass(frozen=True)
class DRRealization:
    """A single concrete draw from DR ranges — used for one episode."""

    mass_scale: float
    friction: float
    restitution: float
    gravity_z: float
    noise_scale: float
    latency_steps: int
    camera_degrade: bool
    action_delay: int
    action_noise_scale: float

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class DRSampler:
    """Draws DRRealization instances from a DRConfig."""

    def __init__(self, config: DRConfig, seed: int | None = None) -> None:
        self._config = config
        self._rng: Generator = np.random.default_rng(seed)

    def sample(self) -> DRRealization:
        c = self._config
        return DRRealization(
            mass_scale=float(self._rng.uniform(*c.mass_scale_range)),
            friction=float(self._rng.uniform(*c.friction_range)),
            restitution=float(self._rng.uniform(*c.restitution_range)),
            gravity_z=float(self._rng.uniform(*c.gravity_z_range)),
            noise_scale=float(self._rng.uniform(*c.noise_scale_range)),
            latency_steps=int(self._rng.integers(c.latency_steps_range[0], c.latency_steps_range[1] + 1)),
            camera_degrade=bool(self._rng.random() < c.camera_degrade_prob),
            action_delay=int(self._rng.integers(c.action_delay_range[0], c.action_delay_range[1] + 1)),
            action_noise_scale=float(self._rng.uniform(*c.action_noise_scale_range)),
        )

    def sample_n(self, n: int) -> list[DRRealization]:
        """Draw n realizations (for batch evaluation)."""
        return [self.sample() for _ in range(n)]
