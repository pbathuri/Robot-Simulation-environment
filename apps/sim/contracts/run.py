"""Run metadata and config (aligned with contracts/v1/run.json)."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SeedsSnapshot(BaseModel):
    main: int | None = None
    physics: int | None = None
    sensors: int | None = None


class MetricsSummary(BaseModel):
    srcc: float | None = None
    replay_error: float | None = None
    task_success_rate: float | None = None
    cumulative_reward: float | None = None


class RunCreate(BaseModel):
    """Payload to create a new run."""

    scenario: str = "default"
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    seeds: SeedsSnapshot | None = None


class RunMetadata(BaseModel):
    """Run metadata as stored and returned by API."""

    run_id: str
    status: RunStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    scenario: str = "default"
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    seeds: SeedsSnapshot | None = None
    git_hash: str | None = None
    asset_versions: dict[str, Any] = Field(default_factory=dict)
    metrics_summary: MetricsSummary | None = None
