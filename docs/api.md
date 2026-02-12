# API

## Versioning

- Base path: `/v1/`. All stable endpoints live under `/v1/`.
- Version in URL; future versions add `/v2/` without breaking v1.
- Deprecation: announce in changelog and response headers; keep v1 supported for at least 6 months.

## Gateway

- **Stack:** FastAPI (Python). Chosen for: single language with sim (Python), native OpenAPI, Pydantic alignment with contracts, async support.
- **OpenAPI:** Generated from route definitions and Pydantic models; served at `/openapi.json` and `/docs`.

## Endpoints (Core)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/health` | Health check |
| POST | `/v1/runs` | Create run (body: scenario, config, options) → returns `run_id` |
| GET | `/v1/runs` | List runs (optional: limit, status, scenario) |
| GET | `/v1/runs/{run_id}` | Run detail (metadata, config summary, metrics) |
| GET | `/v1/runs/{run_id}/metrics` | Metrics for run (JSON) |
| GET | `/v1/runs/{run_id}/replay` | Replay bundle (for re-run or analysis) |
| POST | `/v1/runs/{run_id}/cancel` | Cancel running job (placeholder) |
| GET | `/v1/scenarios` | List available scenarios |

**QERS API (under `/api/`):**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/runs` | List sim runs (from `runs/` dir); unified for dashboard |
| POST | `/api/projects` | Create project |
| GET | `/api/projects` | List projects |
| POST | `/api/assets/import` | Import URDF/USD/mesh |
| GET | `/api/assets` | List assets |
| POST | `/api/design/segment` | Segment asset → parts |
| POST | `/api/design/linkage` | Build linkage; optional export URDF |
| POST | `/api/sim/run` | Start sim run (sync if no Redis; else returns `job_id` queued) |
| GET | `/api/sim/{job_id}/status` | Job status (CREATED/QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELLED) |
| GET | `/api/sim/{job_id}/metrics` | Metrics for job/run |
| GET | `/api/sim/{job_id}/report` | Full report for job/run |
| POST | `/api/sim/{job_id}/cancel` | Cancel a queued or running job |
| GET | `/api/sim/step` | Optional: get step by `run_id` and `step_index` from replay |
| GET | `/api/sim/metrics/{run_id}` | Metrics for run |
| GET | `/api/sim/report/{run_id}` | Full report |
| GET | `/api/benchmarks/latest` | Latest benchmark report (G_dyn, G_perc, G_perf) |
| POST | `/api/ai/plan` | Generate plan from task spec (review only) |
| GET | `/api/reality-profiles` | List reality profiles |

**Batch / Multi-Profile Evaluation:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/sim/batch` | Run sim across N reality profiles; returns batch report with per-profile metrics |
| GET | `/api/sim/batch/{batch_id}` | Retrieve batch report for a multi-profile run |
| GET | `/api/sim/batch/{batch_id}/evaluate` | Compute cross-profile evaluation (performance drops, gap widths) |
| POST | `/api/sim/compare` | Compare metrics across multiple individual runs; pairwise drops |

**Batch request body (`POST /api/sim/batch`):**

```json
{
  "urdf_path": "examples/simple_robot.urdf",
  "profiles": ["default", "slippery_warehouse", "pseudo_reality_A"],
  "steps": 50,
  "dt": 0.01,
  "seed": 42,
  "dr_episodes_per_profile": 3
}
```

**Compare request body (`POST /api/sim/compare`):**

```json
{
  "run_ids": ["run_id_1", "run_id_2"],
  "metric_key": "avg_step_time_ms"
}
```

## Data Contracts

- Request/response bodies conform to schemas in `/contracts` (see `docs/simulation_contracts.md`).
- Use same types for run metadata, metrics, and replay as in sim and eval.

## Auth (Placeholder)

- RBAC placeholder: API key in header or JWT. Document in `docs/security.md`.
- No auth required for local dev; env var to enable auth in production.

## Webhooks

- **Strategy:** Optional webhook URL in run creation; on run completion (or failure), POST to URL with payload: `{ "event": "run.completed", "run_id": "...", "timestamp": "...", "payload": { ... } }`.
- Retry: exponential backoff (e.g. 3 retries); document in API docs.

## Observability

- Request IDs; structured logs (OpenTelemetry-friendly); no secrets in logs.
