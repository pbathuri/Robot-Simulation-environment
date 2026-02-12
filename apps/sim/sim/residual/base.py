"""Residual model interface: predicts delta to add to engine state."""

from abc import ABC, abstractmethod
from typing import Any


class ResidualModel(ABC):
    """Interface for residual dynamics: next_state = engine_next_state + predict_delta(...)."""

    @abstractmethod
    def predict_delta(
        self,
        state: dict[str, Any],
        action: dict[str, Any],
        obs: dict[str, Any],
    ) -> dict[str, Any]:
        """Return state delta to add to engine output. Keys should match state (e.g. joint_positions)."""
        ...
