"""Residual dynamics: next_state = engine_state + f_theta(state, action, obs)."""

from apps.sim.sim.residual.base import ResidualModel
from apps.sim.sim.residual.stub import StubResidualModel
from apps.sim.sim.residual.learned import LearnedResidualModel

__all__ = ["ResidualModel", "StubResidualModel", "LearnedResidualModel"]
