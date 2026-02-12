"""
Model registry: pluggable models by task (VLA, policy, perception, planner).
Uniform interface: predict_action(obs, goal), plan(goal, scene), perceive(sensor_data).
Stub adapters per category for MVP.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseModelAdapter(ABC):
    """Base for registry adapters."""

    @abstractmethod
    def load(self, config: dict[str, Any]) -> None:
        """Load model (local/remote, device, cache)."""
        ...


class VLAdapter(BaseModelAdapter):
    """Vision-Language-Action: predict_action(obs, goal) -> action."""

    def load(self, config: dict[str, Any]) -> None:
        pass

    def predict_action(self, obs: dict[str, Any], goal: str) -> dict[str, Any]:
        """Stub: return zero action."""
        return {"joint_targets": [0.0], "stub": True}


class PolicyAdapter(BaseModelAdapter):
    """Policy (RL): predict_action(obs, goal) -> action."""

    def load(self, config: dict[str, Any]) -> None:
        pass

    def predict_action(self, obs: dict[str, Any], goal: str) -> dict[str, Any]:
        return {"joint_targets": [0.0], "stub": True}


class PerceptionAdapter(BaseModelAdapter):
    """Perception: perceive(sensor_data) -> scene_updates."""

    def load(self, config: dict[str, Any]) -> None:
        pass

    def perceive(self, sensor_data: dict[str, Any]) -> dict[str, Any]:
        return {"objects": [], "stub": True}


class PlannerAdapter(BaseModelAdapter):
    """Planner: plan(goal, scene_graph) -> high_level_plan."""

    def load(self, config: dict[str, Any]) -> None:
        pass

    def plan(self, goal: str, scene_graph: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"action": "stub", "args": {}}]


class ModelRegistry:
    """Register and resolve models by task type. Stub: one adapter per category."""

    def __init__(self) -> None:
        self._adapters: dict[str, BaseModelAdapter] = {
            "vla": VLAdapter(),
            "policy": PolicyAdapter(),
            "perception": PerceptionAdapter(),
            "planner": PlannerAdapter(),
        }

    def get(self, task_type: str) -> BaseModelAdapter | None:
        return self._adapters.get(task_type)

    def predict_action(self, task_type: str, obs: dict[str, Any], goal: str) -> dict[str, Any]:
        adapter = self.get(task_type)
        if adapter and hasattr(adapter, "predict_action"):
            return adapter.predict_action(obs, goal)
        return {"stub": True}

    def plan(self, goal: str, scene_graph: dict[str, Any]) -> list[dict[str, Any]]:
        adapter = self.get("planner")
        if adapter and hasattr(adapter, "plan"):
            return adapter.plan(goal, scene_graph)
        return []

    def perceive(self, sensor_data: dict[str, Any]) -> dict[str, Any]:
        adapter = self.get("perception")
        if adapter and hasattr(adapter, "perceive"):
            return adapter.perceive(sensor_data)
        return {}
