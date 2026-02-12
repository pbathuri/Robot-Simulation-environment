"""Environment registry: list, create, and run benchmark environments."""
from __future__ import annotations
from typing import Any
from apps.sim.envs.base import BaseEnv
from apps.sim.envs.cartpole import CartpoleEnv
from apps.sim.envs.reach import ReachEnv
from apps.sim.envs.walker2d import Walker2DEnv
from apps.sim.envs.push import PushEnv

ENV_REGISTRY: dict[str, type[BaseEnv]] = {
    "cartpole": CartpoleEnv,
    "reach": ReachEnv,
    "walker2d": Walker2DEnv,
    "push": PushEnv,
}


def list_envs() -> list[dict[str, Any]]:
    return [cls.metadata for cls in ENV_REGISTRY.values()]


def make_env(env_id: str, **kwargs: Any) -> BaseEnv:
    cls = ENV_REGISTRY.get(env_id)
    if cls is None:
        raise KeyError(f"Unknown environment: {env_id}. Available: {list(ENV_REGISTRY.keys())}")
    return cls(**kwargs)


def run_episode(
    env_id: str,
    *,
    steps: int = 200,
    seed: int = 42,
    noise_scale: float = 0.0,
    noise_type: str = "gaussian",
    action_mode: str = "sinusoidal",
) -> dict[str, Any]:
    """Run one full episode, return trajectory + metrics."""
    import math
    env = make_env(env_id, seed=seed, noise_scale=noise_scale, noise_type=noise_type)
    obs = env.reset(seed=seed)
    trajectory: list[dict[str, Any]] = []
    total_reward = 0.0
    import numpy as np

    for i in range(steps):
        # Action generation
        if action_mode == "sinusoidal":
            t = i / max(steps, 1)
            action = [math.sin(2 * math.pi * (0.5 + j * 0.3) * t + j) * 0.8 for j in range(env.act_dim)]
        elif action_mode == "random":
            action = env.rng.uniform(-1, 1, env.act_dim).tolist()
        else:
            action = [0.0] * env.act_dim

        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        trajectory.append({
            "step": i,
            "obs": env.obs_to_list(obs),
            "reward": float(reward),
            "action": action,
            "render": env.render_state(),
            "terminated": terminated,
            "truncated": truncated,
        })
        if terminated or truncated:
            break

    return {
        "env_id": env_id,
        "steps_run": len(trajectory),
        "total_reward": float(total_reward),
        "avg_reward": float(total_reward / max(len(trajectory), 1)),
        "noise_scale": noise_scale,
        "noise_type": noise_type,
        "seed": seed,
        "trajectory": trajectory,
    }
