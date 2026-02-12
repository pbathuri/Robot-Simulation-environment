"""Replay bundle: config + actions + seeds for deterministic re-run."""

from typing import Any

from pydantic import BaseModel, Field


class ReplayBundle(BaseModel):
    """Sufficient data to re-run a simulation deterministically."""

    run_id: str
    config: dict[str, Any] = Field(default_factory=dict)
    seeds: dict[str, int] = Field(default_factory=dict)
    initial_state: dict[str, Any] = Field(default_factory=dict)
    actions: list[dict[str, Any]] = Field(default_factory=list)
