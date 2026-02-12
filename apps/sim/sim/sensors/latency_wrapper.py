"""Latency wrapper: delays sensor output by N steps for sim-to-real alignment."""

from collections import deque
from typing import Any

from numpy.random import Generator

from apps.sim.sim.sensors.base import SensorModel


class LatencyWrapper(SensorModel):
    """Wraps a sensor and returns observation from N steps ago."""

    def __init__(self, sensor: SensorModel, latency_steps: int = 0) -> None:
        self._sensor = sensor
        self._latency_steps = max(0, latency_steps)
        self._buffer: deque[dict[str, Any]] = deque(maxlen=self._latency_steps + 1)

    @property
    def name(self) -> str:
        return getattr(self._sensor, "name", "wrapped")

    def observe(
        self,
        state: dict[str, Any],
        t: float,
        *,
        rng: Generator | None = None,
    ) -> dict[str, Any]:
        obs = self._sensor.observe(state, t, rng=rng)
        self._buffer.append(obs)
        if len(self._buffer) > self._latency_steps:
            return self._buffer[0]
        return obs  # Not enough history yet
