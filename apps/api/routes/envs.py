"""Environment benchmark API routes."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/envs", tags=["environments"])


class RunEpisodeRequest(BaseModel):
    steps: int = 200
    seed: int = 42
    noise_scale: float = 0.0
    noise_type: str = "gaussian"
    action_mode: str = "sinusoidal"


class StepRequest(BaseModel):
    action: list[float]


# In-memory env instances for interactive stepping
_active_envs: dict[str, Any] = {}


@router.get("/list")
def list_environments() -> dict[str, Any]:
    from apps.sim.envs.registry import list_envs
    return {"environments": list_envs()}


@router.post("/{env_id}/run")
def run_full_episode(env_id: str, req: RunEpisodeRequest) -> dict[str, Any]:
    from apps.sim.envs.registry import run_episode
    try:
        return run_episode(
            env_id, steps=req.steps, seed=req.seed,
            noise_scale=req.noise_scale, noise_type=req.noise_type,
            action_mode=req.action_mode,
        )
    except KeyError as e:
        raise HTTPException(404, str(e))


@router.post("/{env_id}/reset")
def reset_env(env_id: str, seed: int = 42, noise_scale: float = 0.0, noise_type: str = "gaussian") -> dict[str, Any]:
    from apps.sim.envs.registry import make_env
    try:
        env = make_env(env_id, seed=seed, noise_scale=noise_scale, noise_type=noise_type)
        obs = env.reset(seed=seed)
        session_id = f"{env_id}_{seed}"
        _active_envs[session_id] = env
        return {"session_id": session_id, "obs": obs.tolist(), "render": env.render_state()}
    except KeyError as e:
        raise HTTPException(404, str(e))


@router.post("/{session_id}/step")
def step_env(session_id: str, req: StepRequest) -> dict[str, Any]:
    env = _active_envs.get(session_id)
    if env is None:
        raise HTTPException(404, f"No active session: {session_id}. Call reset first.")
    obs, reward, terminated, truncated, info = env.step(req.action)
    result = {
        "obs": obs.tolist(), "reward": float(reward),
        "terminated": terminated, "truncated": truncated,
        "info": info, "render": env.render_state(),
    }
    if terminated or truncated:
        del _active_envs[session_id]
    return result
