# Contributing

## Setup

- **Python (sim + API):** `python >= 3.10`, venv recommended. Install deps: `pip install -r apps/sim/requirements.txt`, `pip install -r apps/api/requirements.txt`.
- **Node (web):** `node >= 18`, `pnpm` or `npm`. Install: `cd apps/web && pnpm install`.
- **Contracts:** See `/contracts/README.md` for generating Python/TS types from JSON Schema.

## Code Standards

- **Python:** ruff, mypy, pytest. Type hints required; use `numpy.random.Generator` for deterministic randomness.
- **TypeScript:** strict mode; eslint + prettier. API clients from schema where possible.
- No magic constants; central config and documented defaults.
- Single responsibility per module; clear naming.

## Workflow

1. Branch from `main`; small, focused PRs.
2. Before coding: list target files, interface changes, acceptance checks (per AGENTS.md).
3. Run lint and tests before pushing. CI runs: lint, unit tests, smoke sim (if configured).

## Commands

- **Bootstrap:** `/bootstrap_repo` (see `docs/cursor_skills_commands.md`).
- **Add task:** `/add_sim_task` – new scenario + contracts + runner + metrics.
- **Run sims:** `/run_batch_sims` – batch runs with DR; outputs under `runs/`.
- **Eval:** `/compute_eval` – SRCC, replay error, task metrics → dashboard.
- **Calibrate:** `/calibrate_from_real` – ingest real logs, update sim params.

## Docs

- Architecture: `docs/architecture.md`
- Contracts: `docs/simulation_contracts.md`
- Sim2real: `docs/sim2real_playbook.md`
- Evaluation: `docs/evaluation.md`
- API: `docs/api.md`
- Security: `docs/security.md`

## CI

- Lint (ruff, mypy, eslint).
- Unit tests (pytest, jest/vitest).
- Smoke: start API, run one sim, optional: fetch run from API.
- No secrets in repo; use env vars in CI for API keys.
