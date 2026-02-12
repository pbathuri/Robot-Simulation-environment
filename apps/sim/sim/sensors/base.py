"""Sensor model interface: noise, latency, DR knobs."""

from abc import ABC, abstractmethod
from typing import Any

from numpy.random import Generator


class SensorModel(ABC):
    """Produce observations from state; support optional noise and latency."""

    @abstractmethod
    def observe(
        self,
        state: dict[str, Any],
        t: float,
        *,
        rng: Generator | None = None,
    ) -> dict[str, Any]:
        """
        Return observation for current state and time.
        If rng is None, output must be deterministic (no noise).
        """
        ...
