"""
Celery tasks: run_sim (queued simulation).
"""

from __future__ import annotations

from pathlib import Path

from apps.jobs.celery_app import app
from apps.jobs.state import (
    CREATED,
    QUEUED,
    RUNNING,
    SUCCEEDED,
    FAILED,
    CANCELLED,
    get_job_status,
    set_job_status,
    ensure_job_dir,
    TERMINAL_STATUSES,
)


@app.task(bind=True, name="apps.jobs.tasks.run_sim")
def run_sim(
    self,
    job_id: str,
    urdf_path: str,
    steps: int = 100,
    dt: float = 0.01,
    seed: int | None = None,
    use_q_plugin: bool = False,
    use_residual: bool = False,
    reality_profile: str | None = None,
    runs_dir: str | None = None,
) -> dict:
    """
    Run QERS simulation as a background job.
    Writes status RUNNING → SUCCEEDED/FAILED into runs/<job_id>/status.json.
    """
    import os
    if runs_dir is None:
        runs_dir = os.environ.get("RUNS_DIR", str(Path(__file__).resolve().parents[2] / "runs"))

    # Check if already cancelled
    current = get_job_status(job_id)
    if current and current.get("status") == CANCELLED:
        return {"job_id": job_id, "status": CANCELLED, "message": "Job was cancelled"}

    set_job_status(job_id, RUNNING, message="Simulation running")

    try:
        from apps.sim.runner.qers_runner import run_qers_sim

        meta = run_qers_sim(
            urdf_path=urdf_path,
            steps=steps,
            dt=dt,
            seed=seed,
            use_q_plugin=use_q_plugin,
            use_residual=use_residual,
            reality_profile=reality_profile,
            runs_dir=runs_dir,
            run_id=job_id,
        )
        set_job_status(
            job_id,
            SUCCEEDED,
            message="Completed",
            metrics=meta.get("metrics"),
        )
        return {"job_id": job_id, "status": SUCCEEDED, "meta": meta}
    except Exception as e:
        set_job_status(job_id, FAILED, error=str(e))
        raise
