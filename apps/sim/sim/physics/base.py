"""Physics engine interface: sim core depends only on this."""

from abc import ABC, abstractmethod
from typing import Any


class PhysicsEngine(ABC):
    """Common interface for PyBullet, MuJoCo, or stub backends."""

    @abstractmethod
    def step(self, dt: float) -> None:
        """Advance physics by dt (deterministic)."""
        ...

    @abstractmethod
    def get_state(self) -> dict[str, Any]:
        """Return current state (positions, velocities, etc.) in neutral SI units."""
        ...

    @abstractmethod
    def set_state(self, state: dict[str, Any]) -> None:
        """Set state for replay or reset."""
        ...

    @abstractmethod
    def apply_action(self, action: dict[str, Any], dt: float) -> None:
        """Apply control action for this step."""
        ...
