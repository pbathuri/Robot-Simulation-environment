"""
QERS FastAPI backend: /api/projects, /api/assets, /api/design, /api/sim.
Sim runs can be synchronous (no Redis) or queued (Celery + Redis).
"""

import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Paths: allow override via env for Docker/Railway
_def_root = Path(__file__).resolve().parents[2]
RUNS_DIR = Path(os.environ.get("RUNS_DIR", str(_def_root / "runs")))
ASSETS_DIR = Path(os.environ.get("ASSETS_DIR", str(_def_root / "assets")))
EXAMPLES_DIR = Path(os.environ.get("EXAMPLES_DIR", str(_def_root / "examples")))

app = FastAPI(title="LABLAB API", version="2.0.0", description="Quantum-Enhanced Robot Simulator Platform")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount feature routers
from apps.api.routes.envs import router as envs_router
from apps.api.routes.quantum import router as quantum_router
from apps.api.routes.environments import router as env3d_router
from apps.api.routes.code import router as code_router
from apps.api.routes.robodk import router as robodk_router
app.include_router(envs_router)
app.include_router(quantum_router)
app.include_router(env3d_router)
app.include_router(code_router)
app.include_router(robodk_router)


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class SimRunRequest(BaseModel):
    project_id: str
    urdf_path: str
    steps: int = 100
    dt: float = 0.01
    seed: int | None = None
    use_q_plugin: bool = False
    use_residual: bool = False
    reality_profile: str | None = None


class DesignSegmentRequest(BaseModel):
    asset_id: str
    asset_path: str | None = None


class DesignLinkageRequest(BaseModel):
    parts: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    export_urdf: bool = False
    output_filename: str | None = None


class BatchRunRequest(BaseModel):
    urdf_path: str
    profiles: list[str] | None = None  # None = all profiles
    steps: int = 100
    dt: float = 0.01
    seed: int = 42
    use_q_plugin: bool = False
    use_residual: bool = False
    dr_episodes_per_profile: int = 1


class CompareRequest(BaseModel):
    run_ids: list[str]
    metric_key: str = "avg_step_time_ms"


class TaskSpecRequest(BaseModel):
    goal: str
    constraints: list[str] | None = None
    reward_spec: str | None = None
    task_type: str = "custom"


@app.get("/api/health")
@app.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "qers-api"}


@app.post("/api/projects")
def create_project(project: ProjectCreate) -> dict[str, Any]:
    """Create a new project."""
    project_id = f"proj_{project.name.lower().replace(' ', '_')}"
    return {"project_id": project_id, "name": project.name, "description": project.description}


@app.get("/api/projects")
def list_projects() -> dict[str, list[dict[str, Any]]]:
    """List all projects."""
    return {"projects": []}


@app.post("/api/assets/import")
async def import_asset(file: UploadFile = File(...)) -> dict[str, Any]:
    """Import URDF/USD/mesh asset."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = ASSETS_DIR / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return {"asset_id": file.filename, "path": str(file_path), "type": "urdf"}


@app.get("/api/assets")
def list_assets() -> dict[str, list[dict[str, Any]]]:
    """List imported assets."""
    if not ASSETS_DIR.is_dir():
        return {"assets": []}
    assets = []
    for f in ASSETS_DIR.glob("*"):
        if f.is_file():
            assets.append({"asset_id": f.name, "path": str(f), "type": f.suffix[1:]})
    return {"assets": assets}


def _run_sync(request: SimRunRequest) -> dict[str, Any]:
    """Run simulation synchronously (no job queue)."""
    import sys
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from apps.sim.runner.qers_runner import run_qers_sim
    return run_qers_sim(
        urdf_path=request.urdf_path,
        steps=request.steps,
        dt=request.dt,
        seed=request.seed,
        use_q_plugin=request.use_q_plugin,
        use_residual=request.use_residual,
        reality_profile=request.reality_profile,
        runs_dir=str(RUNS_DIR),
    )


@app.post("/api/sim/run")
def run_simulation(request: SimRunRequest) -> dict[str, Any]:
    """
    Start a simulation run. If REDIS_URL is set, enqueues a job and returns job_id.
    Otherwise runs synchronously and returns run metadata.
    """
    if not os.environ.get("REDIS_URL"):
        return _run_sync(request)

    # Queued: create job dir, write CREATED → QUEUED, enqueue task, return job_id
    from apps.jobs.state import ensure_job_dir, set_job_status
    from apps.jobs.state import CREATED, QUEUED
    from apps.jobs.tasks import run_sim

    job_id = str(uuid.uuid4())
    ensure_job_dir(job_id)
    set_job_status(job_id, CREATED, message="Job created")
    task = run_sim.delay(
        job_id=job_id,
        urdf_path=request.urdf_path,
        steps=request.steps,
        dt=request.dt,
        seed=request.seed,
        use_q_plugin=request.use_q_plugin,
        use_residual=request.use_residual,
        reality_profile=request.reality_profile,
        runs_dir=str(RUNS_DIR),
    )
    set_job_status(job_id, QUEUED, message="Queued")
    # Store celery task id in status for cancel/revoke
    status_path = RUNS_DIR / job_id / "status.json"
    if status_path.is_file():
        import json
        with open(status_path) as f:
            data = json.load(f)
        data["celery_id"] = task.id
        data["status"] = QUEUED
        with open(status_path, "w") as f:
            json.dump(data, f, indent=2)
    return {"job_id": job_id, "status": "QUEUED", "message": "Simulation queued"}


@app.get("/api/sim/metrics/{run_id}")
def get_metrics(run_id: str) -> dict[str, Any]:
    """Get metrics for a run."""
    import json
    metrics_path = RUNS_DIR / run_id / "metrics.json"
    if not metrics_path.is_file():
        raise HTTPException(status_code=404, detail="Metrics not found")
    with open(metrics_path) as f:
        return json.load(f)


@app.get("/api/sim/report/{run_id}")
def get_report(run_id: str) -> dict[str, Any]:
    """Get full report (JSON) for a run."""
    import json
    report_path = RUNS_DIR / run_id / "report.json"
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    with open(report_path) as f:
        return json.load(f)


@app.get("/api/sim/{job_id}/status")
def get_job_status(job_id: str) -> dict[str, Any]:
    """Get job status (CREATED/QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELLED)."""
    from apps.jobs.state import get_job_status as _get
    data = _get(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")
    return data


@app.get("/api/sim/{job_id}/metrics")
def get_job_metrics(job_id: str) -> dict[str, Any]:
    """Get metrics for a job (same as run metrics)."""
    return get_metrics(job_id)


@app.get("/api/sim/{job_id}/report")
def get_job_report(job_id: str) -> dict[str, Any]:
    """Get full report for a job (same as run report)."""
    return get_report(job_id)


@app.post("/api/sim/{job_id}/cancel")
def cancel_job(job_id: str) -> dict[str, Any]:
    """Cancel a queued or running job."""
    from apps.jobs.state import get_job_status as _get, set_job_status
    from apps.jobs.state import CANCELLED, TERMINAL_STATUSES

    data = _get(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")
    if data.get("status") in TERMINAL_STATUSES:
        return {"job_id": job_id, "status": data["status"], "message": "Already terminal"}
    set_job_status(job_id, CANCELLED, message="Cancelled by user")
    celery_id = data.get("celery_id")
    if celery_id and os.environ.get("REDIS_URL"):
        from apps.jobs.celery_app import app as celery_app
        celery_app.control.revoke(celery_id, terminate=True)
    return {"job_id": job_id, "status": "CANCELLED", "message": "Cancel requested"}


@app.get("/api/sim/step")
def get_sim_step(run_id: str, step_index: int = 0) -> dict[str, Any]:
    """Get single step from full timeline (by index). For playback/scrubbing."""
    import json
    report_path = RUNS_DIR / run_id / "report.json"
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    with open(report_path) as f:
        report = json.load(f)
    timeline = report.get("timeline", [])
    if step_index < 0 or step_index >= len(timeline):
        raise HTTPException(status_code=404, detail="Step index out of range")
    return {"run_id": run_id, "step_index": step_index, "total_steps": len(timeline), **timeline[step_index]}


@app.get("/api/sim/timeline/{run_id}")
def get_run_timeline(run_id: str, start: int = 0, limit: int = 500) -> dict[str, Any]:
    """Get timeline slice for charts/playback. Returns state at each step."""
    import json
    report_path = RUNS_DIR / run_id / "report.json"
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    with open(report_path) as f:
        report = json.load(f)
    timeline = report.get("timeline", [])
    total = len(timeline)
    sliced = timeline[start:start + limit]
    return {"run_id": run_id, "total_steps": total, "start": start, "count": len(sliced), "timeline": sliced}


@app.get("/api/runs")
def list_runs(limit: int = 50) -> dict[str, Any]:
    """List sim runs (from runs/ dir). Includes job runs (status.json) and completed (report/meta)."""
    import json
    if not RUNS_DIR.is_dir():
        return {"runs": [], "count": 0}
    run_ids = set()
    for d in RUNS_DIR.iterdir():
        if not d.is_dir():
            continue
        if (d / "report.json").is_file() or (d / "meta.json").is_file() or (d / "status.json").is_file():
            run_ids.add(d.name)
    run_ids = sorted(run_ids, reverse=True)[:limit]
    runs = []
    for rid in run_ids:
        # Prefer status.json (job lifecycle) then report.json then meta.json
        status_path = RUNS_DIR / rid / "status.json"
        meta_path = RUNS_DIR / rid / "report.json"
        if not meta_path.is_file():
            meta_path = RUNS_DIR / rid / "meta.json"
        if status_path.is_file():
            try:
                with open(status_path) as f:
                    data = json.load(f)
                runs.append({
                    "run_id": data.get("job_id", rid),
                    "status": data.get("status", "unknown"),
                    "metrics": data.get("metrics", {}),
                })
                continue
            except Exception:
                pass
        if meta_path.is_file():
            try:
                with open(meta_path) as f:
                    data = json.load(f)
                runs.append({
                    "run_id": data.get("run_id", rid),
                    "status": data.get("status", "completed"),
                    "metrics": data.get("metrics", data.get("config", {}).get("metrics", {})),
                })
            except Exception:
                runs.append({"run_id": rid, "status": "completed", "metrics": {}})
    return {"runs": runs, "count": len(runs)}


def _run_meta(rid: str) -> dict[str, Any]:
    """Load run metadata from status.json (job) or report.json or meta.json."""
    import json
    status_path = RUNS_DIR / rid / "status.json"
    if status_path.is_file():
        with open(status_path) as f:
            data = json.load(f)
        metrics_summary = data.get("metrics") or {}
        metrics_json = RUNS_DIR / rid / "metrics.json"
        if metrics_json.is_file():
            with open(metrics_json) as mf:
                metrics_summary = json.load(mf)
        return {
            "run_id": data.get("job_id", rid),
            "status": data.get("status", "unknown"),
            "scenario": "sim",
            "config_snapshot": None,
            "seeds": None,
            "metrics_summary": metrics_summary,
            "run_dir": str(RUNS_DIR / rid),
        }
    for name in ("report.json", "meta.json"):
        p = RUNS_DIR / rid / name
        if p.is_file():
            with open(p) as f:
                data = json.load(f)
            metrics_path = RUNS_DIR / rid / "metrics.json"
            metrics_summary = {}
            if metrics_path.is_file():
                with open(metrics_path) as mf:
                    metrics_summary = json.load(mf)
            return {
                "run_id": data.get("run_id", rid),
                "status": data.get("status", "completed"),
                "scenario": data.get("scenario", data.get("config", {}).get("scenario", "sim")),
                "config_snapshot": data.get("config"),
                "seeds": data.get("seeds"),
                "metrics_summary": metrics_summary,
                "run_dir": str(RUNS_DIR / rid),
            }
    raise HTTPException(status_code=404, detail="Run not found")


@app.get("/v1/runs")
def v1_list_runs(limit: int = 50) -> dict[str, Any]:
    """List runs (v1 shape for dashboard)."""
    out = list_runs(limit=limit)
    runs = out["runs"]
    v1_runs = []
    for r in runs:
        rid = r.get("run_id", "")
        try:
            v1_runs.append(_run_meta(rid))
        except HTTPException:
            v1_runs.append({"run_id": rid, "status": r.get("status", "completed"), "scenario": "sim"})
    return {"runs": v1_runs, "count": len(v1_runs)}


@app.get("/v1/runs/{run_id}")
def v1_get_run(run_id: str) -> dict[str, Any]:
    """Run detail for UI."""
    return _run_meta(run_id)


@app.get("/v1/runs/{run_id}/metrics")
def v1_get_run_metrics(run_id: str) -> dict[str, Any]:
    """Metrics for run (v1)."""
    return get_metrics(run_id)


@app.post("/api/design/segment")
def design_segment(req: DesignSegmentRequest) -> dict[str, Any]:
    """Segment asset (mesh/URDF) into parts. Stub: single part or link list."""
    import sys
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from apps.sim.design.segment import segment_asset
    path = req.asset_path or str(ASSETS_DIR / req.asset_id)
    if not Path(path).is_file():
        path = str(repo_root / "examples" / req.asset_id) if (repo_root / "examples" / req.asset_id).is_file() else path
    return segment_asset(path)


@app.post("/api/design/linkage")
def design_linkage(req: DesignLinkageRequest) -> dict[str, Any]:
    """Build linkage spec from parts + edges; optionally export URDF."""
    import sys
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from apps.sim.design.linkage import build_linkage_spec, export_linkage_to_urdf
    spec = build_linkage_spec(req.parts, req.edges)
    if req.export_urdf:
        out_name = req.output_filename or "exported_robot.urdf"
        out_path = ASSETS_DIR / out_name
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        export_linkage_to_urdf(spec, out_path)
        spec["exported_path"] = str(out_path)
    return spec


@app.post("/api/ai/plan")
def ai_plan(req: TaskSpecRequest) -> dict[str, Any]:
    """Generate plan from task spec. Output for review only; no execution."""
    import sys
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from apps.agents.planner import plan_from_task_spec
    task_spec = {"goal": req.goal, "constraints": req.constraints or [], "reward_spec": req.reward_spec, "task_type": req.task_type}
    return plan_from_task_spec(task_spec)


# ── Batch / Multi-Profile Evaluation ─────────────────────────────────────────


@app.post("/api/sim/batch")
def run_batch_simulation(request: BatchRunRequest) -> dict[str, Any]:
    """
    Run simulation across multiple reality profiles (pseudo-reality evaluation).
    Returns batch_id and per-profile results.

    Inspired by Ligot & Birattari (2019): design on one model, evaluate on
    multiple pseudo-realities to assess robustness without real hardware.
    """
    import sys
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from apps.sim.runner.batch_runner import run_batch
    try:
        report = run_batch(
            request.urdf_path,
            profiles=request.profiles,
            steps=request.steps,
            dt=request.dt,
            seed=request.seed,
            use_q_plugin=request.use_q_plugin,
            use_residual=request.use_residual,
            dr_episodes_per_profile=request.dr_episodes_per_profile,
            runs_dir=str(RUNS_DIR),
        )
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/sim/batch/{batch_id}")
def get_batch_report(batch_id: str) -> dict[str, Any]:
    """Get batch report for a multi-profile run."""
    import json
    report_path = RUNS_DIR / batch_id / "batch_report.json"
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="Batch report not found")
    with open(report_path) as f:
        return json.load(f)


@app.get("/api/sim/batch/{batch_id}/evaluate")
def evaluate_batch(batch_id: str) -> dict[str, Any]:
    """
    Compute cross-profile evaluation (performance drop, gap width) for a batch.
    Requires the batch report to exist.
    """
    import json
    import sys
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from apps.sim.eval.batch_eval import evaluate_batch_report

    report_path = RUNS_DIR / batch_id / "batch_report.json"
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="Batch report not found")
    with open(report_path) as f:
        batch_report = json.load(f)
    try:
        return evaluate_batch_report(batch_report)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/sim/compare")
def compare_runs(request: CompareRequest) -> dict[str, Any]:
    """
    Compare metrics across multiple individual runs.
    Returns per-run metric values and pairwise performance drops.
    """
    import json
    from apps.sim.eval.batch_eval import compute_performance_drop

    run_metrics: list[dict[str, Any]] = []
    for rid in request.run_ids:
        metrics_path = RUNS_DIR / rid / "metrics.json"
        if not metrics_path.is_file():
            run_metrics.append({"run_id": rid, "error": "metrics not found"})
            continue
        with open(metrics_path) as f:
            m = json.load(f)
        run_metrics.append({"run_id": rid, "metrics": m})

    # Pairwise drops
    pairwise: list[dict[str, Any]] = []
    valid = [rm for rm in run_metrics if "metrics" in rm]
    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            drop = compute_performance_drop(
                valid[i]["metrics"], valid[j]["metrics"], metric_key=request.metric_key
            )
            pairwise.append({
                "run_a": valid[i]["run_id"],
                "run_b": valid[j]["run_id"],
                "drop": drop,
            })

    return {
        "runs": run_metrics,
        "pairwise_drops": pairwise,
        "metric_key": request.metric_key,
    }


# ── Adversarial Search ───────────────────────────────────────────────────────


class AdversarialRequest(BaseModel):
    urdf_path: str
    profile: str = "default"
    steps: int = 50
    seed: int = 42
    max_iterations: int = 30
    population_size: int = 8


@app.post("/api/sim/adversarial")
def run_adversarial(request: AdversarialRequest) -> dict[str, Any]:
    """Run SAGE-like adversarial search to find worst-case environment params."""
    import sys
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from apps.sim.sim.adversarial import run_adversarial_evaluation
    from apps.sim.profiles.loader import load_profile

    profile = load_profile(request.profile) or {}
    try:
        return run_adversarial_evaluation(
            request.urdf_path, profile,
            steps=request.steps, seed=request.seed,
            max_iterations=request.max_iterations,
            population_size=request.population_size,
            runs_dir=str(RUNS_DIR),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Gap Metrics ──────────────────────────────────────────────────────────────


class GapMetricsRequest(BaseModel):
    design_run_id: str
    eval_run_id: str


@app.post("/api/sim/gap-metrics")
def compute_gap(request: GapMetricsRequest) -> dict[str, Any]:
    """Compute G_dyn, G_perc, G_perf between two runs."""
    import json as _json
    import sys
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from apps.sim.eval.gap_metrics import compute_all_gap_metrics

    def _load_run(run_id: str) -> dict[str, Any]:
        report_path = RUNS_DIR / run_id / "report.json"
        metrics_path = RUNS_DIR / run_id / "metrics.json"
        run_data: dict[str, Any] = {}
        if report_path.is_file():
            with open(report_path) as f:
                report = _json.load(f)
            run_data["timeline"] = report.get("timeline_summary", [])
        if metrics_path.is_file():
            with open(metrics_path) as f:
                run_data["metrics"] = _json.load(f)
        return run_data

    design = _load_run(request.design_run_id)
    eval_data = _load_run(request.eval_run_id)

    if not design or not eval_data:
        raise HTTPException(status_code=404, detail="One or both runs not found")

    return compute_all_gap_metrics(design, eval_data)


# ── System Info ──────────────────────────────────────────────────────────────


@app.get("/api/system/info")
def system_info() -> dict[str, Any]:
    """Return system capabilities for the dashboard."""
    import platform
    try:
        import pybullet
        pybullet_version = pybullet.getPhysicsEngineParameters.__doc__[:20] if hasattr(pybullet, 'getPhysicsEngineParameters') else "available"
    except ImportError:
        pybullet_version = None

    try:
        import qiskit
        qiskit_version = qiskit.__version__
    except ImportError:
        qiskit_version = None

    profiles_count = 0
    try:
        from apps.sim.profiles.loader import list_profiles
        profiles_count = len(list_profiles())
    except Exception:
        pass

    runs_count = 0
    if RUNS_DIR.is_dir():
        runs_count = sum(1 for d in RUNS_DIR.iterdir() if d.is_dir())

    return {
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "pybullet": pybullet_version,
        "qiskit": qiskit_version,
        "physics_engine": "pybullet" if pybullet_version else "stub",
        "profiles_count": profiles_count,
        "runs_count": runs_count,
        "redis_connected": bool(os.environ.get("REDIS_URL")),
    }


# ── Benchmarks ───────────────────────────────────────────────────────────────


@app.get("/api/benchmarks/latest")
def get_benchmark_report() -> dict[str, Any]:
    """Return latest benchmark report (benchmark_report.json) if present."""
    import json
    report_path = Path(__file__).resolve().parents[2] / "benchmark_report.json"
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="No benchmark report found. Run make benchmark first.")
    with open(report_path) as f:
        return json.load(f)


@app.get("/api/reality-profiles")
def list_reality_profiles() -> dict[str, list[dict[str, Any]]]:
    """List available reality profiles from examples/reality_profiles."""
    try:
        from apps.sim.profiles.loader import list_profiles
        profiles = list_profiles()
    except Exception:
        profiles = [
            {"id": "default", "name": "Default", "description": "Standard physics"},
            {"id": "slippery_warehouse", "name": "Slippery Warehouse", "description": "Low friction, 50ms latency"},
        ]
    return {"profiles": profiles}
