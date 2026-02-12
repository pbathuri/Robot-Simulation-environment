"""Sampler and Optimizer interfaces; quantum backends implement these."""

from abc import ABC, abstractmethod
from typing import Any, Callable


class Sampler(ABC):
    """Stochastic process sampler. Quantum or classical implementations."""

    @abstractmethod
    def sample(self, params: dict[str, Any], n: int, *, seed: int | None = None) -> list[float]:
        """Return n samples from the process. Must be reproducible when seed is set."""
        ...


class Optimizer(ABC):
    """Parameter search / calibration. Quantum or classical implementations."""

    @abstractmethod
    def minimize(
        self,
        objective: Callable[[dict[str, float]], float],
        bounds: dict[str, tuple[float, float]],
        *,
        max_evals: int = 100,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """Minimize objective over bounded params. Return best params and value."""
        ...
