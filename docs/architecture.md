# LABLAB – Architecture

## Overview

LABLAB is a robot simulator platform designed to reduce the sim-to-real "reality gap" through stochastic modeling, domain randomization, system identification, residual learning, and standardized evaluation (SRCC, replay error, task metrics). It includes an optional quantum-inspired module for sampling/optimization experiments.

## Monorepo Layout: Why `apps/`

We use an **apps-based monorepo** (not `packages/`) because:

- **Three deployable units:** (1) simulation core service, (2) API gateway, (3) web dashboard. Each is an "app" with its own run script and optional deployment artifact.
- **Shared contracts at repo root:** `/contracts` holds the single source of truth for schemas; we generate types for both Python (sim, API) and TypeScript (web). This keeps boundaries clear without a separate "packages" layer.
- **Language split:** Python for sim + API (single toolchain, FastAPI fits naturally with Pydantic contracts); TypeScript/Next.js for web. A single `apps/` folder makes it obvious what you run (`apps/sim`, `apps/api`, `apps/web`).

## Bounded Contexts

| Context | Location | Responsibility |
|--------|----------|----------------|
| **sim-core** | `apps/sim/sim/` | Deterministic/stochastic stepping, state/obs/action handling, plugin orchestration |
| **physics-adapters** | `apps/sim/sim/physics/` | PyBullet/MuJoCo/etc. behind common interface |
| **sensors** | `apps/sim/sim/sensors/` | Camera, LiDAR, IMU models with noise/latency/DR |
| **control/policies** | `apps/sim/sim/control/`, `ml/` | Low-level control vs high-level policy; action space |
| **run-orchestration** | `apps/sim/runner/` | Scenario runner, batch parallelism (multiprocessing/Ray) |
| **eval** | `apps/sim/eval/` or `eval/` | SRCC, replay error, task metrics, report generation |
| **api** | `apps/api/` | REST/WebSocket gateway, run CRUD, metrics, webhooks |
| **web** | `apps/web/` | Next.js dashboard: runs list, run detail, metrics charts, teleop placeholder |

All cross-boundary data is defined in **versioned contracts** under `/contracts`.

## Data Flow

1. **Run creation:** API receives run request → creates run record → (optional) enqueues sim job or runs inline.
2. **Sim execution:** Runner loads scenario + config → instantiates sim core with physics/sensor adapters → steps (deterministic or stochastic) → emits telemetry + replay bundle to `/runs/<run_id>/`.
3. **Eval:** Eval service reads run bundles and reference data → computes SRCC, replay error, task metrics → writes reports (JSON/CSV) → API exposes to dashboard.
4. **Dashboard:** Web app fetches runs and metrics from API; displays list, detail, charts; teleop sends commands via API.

## Plugin System

- **Physics engine adapters:** Implement `PhysicsEngine` interface (e.g. `step(dt)`, `get_state()`, `set_state()`). Conformance tests ensure deterministic behavior and state round-trip.
- **Sensor models:** Implement `SensorModel` interface; produce observations per contract; support noise, latency, and DR knobs.
- **Quantum module:** Optional; `Sampler` and `Optimizer` interfaces with classical fallback. Core sim does not depend on quantum tooling.

## Observability & Replay

- Every run produces: **config snapshot**, **seed(s)**, **env/code version** (git hash), **timeline events**, **metrics**.
- Replay: re-run simulation from logged actions + seed; artifacts under `runs/<run_id>/`.

## References

- **Full spec (functions, logic, math):** `docs/qers_spec_reference.md` — single reference for metrics (G_dyn, G_perc, G_perf), APIs, contracts, core algorithms, and phases.
- Reality gap and domain randomization: see `docs/sim2real_playbook.md`.
- Contracts and schemas: `docs/simulation_contracts.md`, `/contracts`.
- API and security: `docs/api.md`, `docs/security.md`.
