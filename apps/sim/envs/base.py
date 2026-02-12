"""
Base environment interface (Gymnasium-compatible).

Every benchmark environment implements:
  reset(seed) -> observation
  step(action) -> (observation, reward, terminated, truncated, info)
  render_state() -> dict   (serializable state for 3D viewport)
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
import numpy as np


class BaseEnv(ABC):
    """Abstract base for all LABLAB benchmark environments."""

    metadata: dict[str, Any] = {}

    def __init__(self, *, seed: int | None = None, dt: float = 0.02) -> None:
        self.dt = dt
        self.rng = np.random.default_rng(seed)
        self.step_count = 0
        self.max_steps = 500

    @property
    @abstractmethod
    def obs_dim(self) -> int: ...

    @property
    @abstractmethod
    def act_dim(self) -> int: ...

    @abstractmethod
    def reset(self, seed: int | None = None) -> np.ndarray: ...

    @abstractmethod
    def step(self, action: np.ndarray | list[float]) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]: ...

    @abstractmethod
    def render_state(self) -> dict[str, Any]:
        """Return serializable dict for 3D rendering."""
        ...

    def obs_to_list(self, obs: np.ndarray) -> list[float]:
        return obs.tolist()
