"""Metrics payload (aligned with contracts/v1/metrics.json)."""

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class MetricsPayload(BaseModel):
    """Evaluation metrics for a run."""

    run_id: str
    srcc: float | None = None
    replay_error: float | None = None
    replay_error_units: str = "m"
    task_success_rate: float | None = None
    cumulative_reward: float | None = None
    fid: float | None = None
    kid: float | None = None
    ssim: float | None = None
    computed_at: datetime = Field(default_factory=datetime.utcnow)
