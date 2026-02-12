"""
Planner stub: task spec (JSON) -> high-level plan (controller skeleton, reward, env modifiers, eval plan).
No execution; output is for review UI only.
"""

from typing import Any


def plan_from_task_spec(task_spec: dict[str, Any]) -> dict[str, Any]:
    """
    Input: task_spec with goal, constraints?, reward_spec?, task_type?
    Output: plan with steps, controller_interface, reward_spec, env_modifiers, evaluation_plan.
    Stub: returns fixed structure; real impl would call LLM or planning model.
    """
    goal = task_spec.get("goal", "")
    task_type = task_spec.get("task_type", "custom")
    return {
        "plan_version": "0.1",
        "goal_summary": goal[:200] if goal else "No goal",
        "task_type": task_type,
        "steps": [
            {"id": "1", "description": "Initialize robot state", "controller_hook": "reset"},
            {"id": "2", "description": "Execute task loop", "controller_hook": "step"},
        ],
        "controller_interface": {
            "reset": "() -> None",
            "step": "(obs: dict) -> action: dict",
        },
        "reward_spec": task_spec.get("reward_spec", "distance_to_goal"),
        "env_modifiers": [],
        "evaluation_plan": {"metrics": ["success_rate", "cumulative_reward"], "num_episodes": 10},
        "approved": False,
    }
