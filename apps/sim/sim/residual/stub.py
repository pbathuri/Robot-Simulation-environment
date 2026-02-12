"""Stub residual: returns zero delta (no correction). Can be replaced by MLP or trained model."""

from typing import Any

from apps.sim.sim.residual.base import ResidualModel


class StubResidualModel(ResidualModel):
    """Zero residual; training hook can replace with learned f_theta."""

    def predict_delta(
        self,
        state: dict[str, Any],
        action: dict[str, Any],
        obs: dict[str, Any],
    ) -> dict[str, Any]:
        joint_positions = state.get("joint_positions", [])
        if joint_positions:
            return {"joint_positions": [0.0] * len(joint_positions)}
        return {}
