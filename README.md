# QERS – Quantum-Enhanced Robotics Simulator

**Goal:** Build a working robotics simulator that narrows the "stochastic reality gap" by combining classical physics (macro-physics) with a quantum-stochastic + adversarial + residual-learning layer (micro-stochasticity), plus an AI/LLM-driven "text → algorithm" workflow.

## Key Differentiators

- **"Reinvent noise, not gravity"** – Build on PyBullet/MuJoCo, overlay Q-Plugin quantum noise + Bayesian sandbox + SAGE adversary + residual dynamics
- **POMDP-based gap metrics:** G_dyn, G_perc, G_perf
- **Design mode:** Mesh import → segmentation → linkage → URDF export via NLP
- **AI text→algorithm:** NLP spec → structured task JSON → planner → controller skeleton
- **Model registry:** Hugging Face models (VLA, policies, perception, planners)
- **Reality Profiles:** Configurable physics + sensor + actuation profiles

## Repo Layout

```
.cursor/rules/          # Cursor rule files (.mdc)
contracts/              # Versioned schemas
docs/                   # architecture, api, evaluation, design mode, AI workflow
apps/
  sim/                  # Simulation core: physics adapters, Q-Plugin, residual, adversary
  api/                  # FastAPI: /api/projects, /api/assets, /api/design, /api/sim
  web/                  # Next.js: Dashboard, Design, Sim, Models, Benchmarks (Three.js viewport)
  agents/               # AI agents: planner, controller generator, design assistant
tools/
  llm_research/         # Multi-LLM provider, caching, prompts
  benchmarks/           # G_dyn, G_perc, G_perf computation scripts
examples/               # Demo URDFs, environments, reality profiles
runs/                   # Run outputs (created at runtime)
```

## Quick Start (MVP Demo)

**Run all commands from the repo root** (the directory containing `Makefile` and `apps/`).

```bash
# Setup (from repo root; requires Node.js/npm for the UI)
python3 -m venv .venv
source .venv/bin/activate
make setup
```

Then in **two terminals** (from repo root, with venv activated):

- Terminal 1: `make backend`
- Terminal 2: `make ui`

Optional: `make demo` to run the example sim.

Open http://localhost:3000 → loads example robot → runs sim → shows metrics + logs.

**Note:** If you paste multi-line blocks into zsh, run one command per line to avoid parse errors. Use `make setup` for a single install step. The UI step uses `pnpm` if available, otherwise `npm` (Node.js must be installed).

**Python 3.13 / macOS:** Core install works without PyBullet or open3d. The sim uses **stub physics** when PyBullet isn’t installed. For real physics, try `pip install -r requirements-optional.txt` (pybullet may fail to build from source on macOS; use Docker or Python 3.11/3.12 if needed). open3d has no 3.13 wheel yet.

## Docker (optional — requires Docker Desktop)

Docker is **not required** for local development. If you have Docker Desktop installed:

```bash
# Dev: backend + web + Redis + worker
docker compose up --build

# Production-style: root Dockerfiles, restart policies
docker compose -f docker-compose.prod.yml up --build
```

- **Web:** http://localhost:3000 — **API:** http://localhost:8000 — **Docs:** http://localhost:8000/docs  
- Sim runs are queued (Celery + Redis) and processed by the worker. See [docs/deploy.md](docs/deploy.md).

**No Docker?** Use `make backend` + `make ui` — everything works locally without Docker or Redis (runs execute synchronously).

## Tech Stack

- **Backend:** Python (FastAPI) + ROS2 bridge (optional for MVP)
- **Physics:** PyBullet (MVP), adapter interface for MuJoCo/Isaac/Webots/Gazebo
- **Quantum:** Qiskit (simulator), classical fallback
- **ML:** PyTorch
- **UI:** Next.js + Three.js (3D viewport)
- **Models:** Hugging Face registry (VLA, policies, perception)

## Multi-Profile / Pseudo-Reality Evaluation (Phase 3)

Run the same scenario across multiple reality profiles to assess robustness without real hardware — inspired by [Ligot & Birattari 2019](https://iridia.ulb.ac.be/supp/IridiaSupp2019-002).

```bash
# Run batch across all profiles (from repo root, backend running)
curl -X POST http://localhost:8000/api/sim/batch \
  -H 'Content-Type: application/json' \
  -d '{"urdf_path":"examples/simple_robot.urdf","steps":50,"dr_episodes_per_profile":3}'

# Or use the Compare page: http://localhost:3000/compare
```

**Available reality profiles:** default, slippery_warehouse, noisy_outdoor, high_fidelity_lab, pseudo_reality_A, pseudo_reality_B

**Domain Randomization:** Each profile defines gap_knobs (friction range, noise range, latency, etc.). The batch runner draws concrete DR realizations per episode, runs the sim, and computes cross-profile metrics (performance drop, gap width, rank stability).

## Tests

```bash
# From repo root, with venv activated:
make test
# Or:
PYTHONPATH=. pytest apps/sim/tests/ -v
```

## Acceptance Criteria (MVP)

- ✅ `make demo` starts backend + UI; loads example URDF; runs sim; metrics show step time and noise
- ✅ User can toggle mechanisms (classical DR vs Q-Plugin fallback)
- ✅ `make benchmark` outputs JSON report with success rate + G_perf proxy
- ✅ Batch runner: run scenario across N profiles, aggregate metrics, compute cross-profile stats
- ✅ Domain randomization: DRConfig + DRSampler draw concrete params from gap_knobs per episode
- ✅ Eval metrics: performance drop, gap width (L1/L2/cosine), rank stability across profiles
- ✅ Compare page: multi-profile batch controls, results table, bar chart, pairwise evaluation

See `docs/architecture.md` for full architecture and `docs/research_context_and_next_phase.md` for literature grounding.

## LABLAB API (RoboDK integration)

The API includes **RoboDK integration** and a **design store**: import from RoboDK, manipulate objects via API, sync poses back. Endpoints under `/api/robodk/` (status, station, import, design objects, sync, add-file, export).

- **Docs:** [docs/DEPLOY.md](docs/DEPLOY.md) (Docker, Railway), [docs/ROBODK_INTEGRATION.md](docs/ROBODK_INTEGRATION.md) (API reference)
- **Verify API:** `make verify` or `./scripts/verify-api.sh 8000` (use port 8001 if API is mapped there)
- **Endpoints:** `/health`, `/api/robodk/status`, `/api/robodk/design/objects`
