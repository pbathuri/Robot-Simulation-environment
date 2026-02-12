"""
Job state stored in runs/<job_id>/status.json.
Lifecycle: CREATED → QUEUED → RUNNING → SUCCEEDED | FAILED | CANCELLED.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Status enum values
CREATED = "CREATED"
QUEUED = "QUEUED"
RUNNING = "RUNNING"
SUCCEEDED = "SUCCEEDED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"

JobStatus = str  # one of the above

TERMINAL_STATUSES = (SUCCEEDED, FAILED, CANCELLED)


def _runs_dir() -> Path:
    import os
    default = Path(__file__).resolve().parents[2] / "runs"
    return Path(os.environ.get("RUNS_DIR", str(default)))


def _status_path(job_id: str) -> Path:
    return _runs_dir() / job_id / "status.json"


def ensure_job_dir(job_id: str) -> Path:
    """Create runs/<job_id> and return the path."""
    d = _runs_dir() / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_job_status(job_id: str) -> dict[str, Any] | None:
    """Read status from runs/<job_id>/status.json. Returns None if not found."""
    p = _status_path(job_id)
    if not p.is_file():
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def set_job_status(
    job_id: str,
    status: JobStatus,
    *,
    message: str | None = None,
    metrics: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """Write status to runs/<job_id>/status.json."""
    ensure_job_dir(job_id)
    p = _status_path(job_id)
    now = datetime.now(tz=timezone.utc).isoformat()
    data: dict[str, Any] = {
        "job_id": job_id,
        "status": status,
        "updated_at": now,
    }
    if message:
        data["message"] = message
    if metrics is not None:
        data["metrics"] = metrics
    if error is not None:
        data["error"] = error
    # Preserve existing created_at / celery_id if present
    if p.is_file():
        try:
            with open(p) as f:
                existing = json.load(f)
            data.setdefault("created_at", existing.get("created_at", now))
            data.setdefault("celery_id", existing.get("celery_id"))
        except (json.JSONDecodeError, OSError):
            pass
    if "created_at" not in data:
        data["created_at"] = now
    with open(p, "w") as f:
        json.dump(data, f, indent=2)
