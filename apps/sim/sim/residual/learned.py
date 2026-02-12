"""
Learned residual model: loads a small MLP to predict state deltas.

Implements the NAS (Neural-Augmented Simulation) concept from Golemo et al. (2018):
    corrected_state = sim_state + f_theta(state, action, observation)

Usage:
    model = LearnedResidualModel.from_checkpoint("path/to/model.pt")
    delta = model.predict_delta(state, action, obs)
    # Apply: new_state[k] += delta[k]
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from apps.sim.sim.residual.base import ResidualModel

logger = logging.getLogger(__name__)


class LearnedResidualModel(ResidualModel):
    """
    MLP-based residual model.

    Architecture: [state_dim + action_dim] -> hidden -> hidden -> state_dim
    Trained offline on paired (sim_state, real_state) data to predict
    delta = real_state - sim_state.
    """

    def __init__(
        self,
        weights: dict[str, Any] | None = None,
        *,
        state_keys: list[str] | None = None,
        action_keys: list[str] | None = None,
        hidden_dim: int = 64,
    ) -> None:
        self._weights = weights
        self._state_keys = state_keys or ["x", "v"]
        self._action_keys = action_keys or ["v"]
        self._hidden_dim = hidden_dim
        self._model = None

        if weights is not None:
            self._build_model(weights)

    def _build_model(self, weights: dict[str, Any]) -> None:
        """Build numpy-based MLP from weight dict (for inference without torch)."""
        self._w1 = np.array(weights["w1"])
        self._b1 = np.array(weights["b1"])
        self._w2 = np.array(weights["w2"])
        self._b2 = np.array(weights["b2"])
        self._w3 = np.array(weights["w3"])
        self._b3 = np.array(weights["b3"])
        self._model = True
        logger.info("Loaded residual MLP: %s -> %s -> %s -> %s",
                     self._w1.shape[1], self._w1.shape[0], self._w2.shape[0], self._w3.shape[0])

    def _forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass through MLP."""
        h = np.tanh(self._w1 @ x + self._b1)
        h = np.tanh(self._w2 @ h + self._b2)
        return self._w3 @ h + self._b3

    def _state_to_vec(self, state: dict[str, Any]) -> np.ndarray:
        vals = []
        for k in self._state_keys:
            v = state.get(k, 0.0)
            if isinstance(v, (list, tuple)):
                vals.extend(v)
            else:
                vals.append(float(v))
        return np.array(vals, dtype=np.float64)

    def _action_to_vec(self, action: dict[str, Any]) -> np.ndarray:
        vals = []
        for k in self._action_keys:
            v = action.get(k, 0.0)
            if isinstance(v, (list, tuple)):
                vals.extend(v)
            else:
                vals.append(float(v))
        return np.array(vals, dtype=np.float64)

    def predict_delta(
        self,
        state: dict[str, Any],
        action: dict[str, Any],
        obs: dict[str, Any],
    ) -> dict[str, Any]:
        """Predict state correction delta. Returns zero if no model loaded."""
        if self._model is None:
            # No trained model: return zero delta (same as stub)
            joint_positions = state.get("joint_positions", [])
            if joint_positions:
                return {"joint_positions": [0.0] * len(joint_positions)}
            return {}

        s_vec = self._state_to_vec(state)
        a_vec = self._action_to_vec(action)
        inp = np.concatenate([s_vec, a_vec])
        delta_vec = self._forward(inp)

        # Map back to state keys
        result: dict[str, Any] = {}
        idx = 0
        for k in self._state_keys:
            v = state.get(k, 0.0)
            if isinstance(v, (list, tuple)):
                n = len(v)
                result[k] = delta_vec[idx:idx + n].tolist()
                idx += n
            else:
                result[k] = float(delta_vec[idx])
                idx += 1
        return result

    @classmethod
    def from_checkpoint(cls, path: str | Path) -> LearnedResidualModel:
        """Load model from a .npz checkpoint."""
        p = Path(path)
        if not p.is_file():
            logger.warning("Residual checkpoint %s not found, using zero-delta.", p)
            return cls(weights=None)

        data = np.load(str(p), allow_pickle=True)
        weights = {k: data[k] for k in data.files}
        # Expect metadata in npz: state_keys, action_keys
        state_keys = weights.pop("state_keys", None)
        action_keys = weights.pop("action_keys", None)
        if state_keys is not None:
            state_keys = state_keys.tolist()
        if action_keys is not None:
            action_keys = action_keys.tolist()
        return cls(weights=weights, state_keys=state_keys, action_keys=action_keys)

    @staticmethod
    def create_random_weights(
        state_dim: int, action_dim: int, hidden_dim: int = 64, seed: int = 0
    ) -> dict[str, Any]:
        """Create small random weights (for testing). Scale near zero so delta ≈ 0."""
        rng = np.random.default_rng(seed)
        scale = 0.001
        return {
            "w1": rng.normal(0, scale, (hidden_dim, state_dim + action_dim)),
            "b1": np.zeros(hidden_dim),
            "w2": rng.normal(0, scale, (hidden_dim, hidden_dim)),
            "b2": np.zeros(hidden_dim),
            "w3": rng.normal(0, scale, (state_dim, hidden_dim)),
            "b3": np.zeros(state_dim),
        }
