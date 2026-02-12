# LABLAB – Robot Simulator: Agent Instructions

This document defines global instructions for AI agents (including Cursor) working in this repository.

## A. Architecture & Boundaries

- Treat the simulator as **bounded contexts**: sim-core, physics-adapters, sensors, controllers/policies, run-orchestration, eval, api, web.
- **Cross-boundary data** must use versioned contracts (JSON Schema or Pydantic models). Schemas live in `/contracts`; generate types for TypeScript and Python.
- The simulator must be **reproducible**: deterministic mode must exist; stochastic mode must be seedable; record seeds in run metadata.

## B. Reality-Gap Taxonomy

- Explicitly model and track gaps: **dynamics**, **perception/sensing**, **actuation/control**, **system design/implementation**.
- For each module, maintain a **"gap knobs"** configuration for domain randomization (mass, friction, restitution, delays, noise, lighting, textures, sensor artifacts, controller filters, packet loss/latency, etc.).
- Provide a **calibration loop**: compare sim vs real logs (when available), update parameters (system identification), plus option for residual learning.

## C. Sim-to-Real Recipe (Workflow)

Docs and commands must implement this loop:

1. Identify task variables + required states/observations/actions.
2. Implement baseline sim fidelity.
3. Add gap-reduction: calibration + improved sensor/actuation models where possible.
4. Add gap-overcoming: domain randomization + adaptation + modular policies.
5. Train/test in parallel sims.
6. Evaluate in target env.
7. Iterate parameters based on real performance + retrain.

## D. Evaluation Discipline

- Implement placeholders + schemas for:
  - **SRCC** (sim-to-real correlation coefficient)
  - **Offline replay error** (roll real actions in sim, compute trajectory error)
  - **Perception similarity** (FID/KID/SSIM placeholders; full impl only if requested)
  - **Task metrics** (success rate, cumulative reward)
- All evaluation output must be machine-readable and visible in the web UI.

## E. Coding Standards

- **Python**: ruff + mypy + pytest; type hints mandatory; no hidden globals; pure functions where possible; deterministic random via `numpy.random.Generator`.
- **TypeScript**: strict; eslint + prettier; API clients generated from schema where feasible.
- Clear module naming and single responsibility.
- No magic constants: central config and documented defaults.

## F. Observability & Replay

- Every sim run produces: config snapshot, seed(s), env asset versions, code version (git hash), timeline events, metrics.
- **Replay**: re-run from logged actions + seed; store under `/runs/<run_id>/`.

## G. Security & Productization

- API keys for LLMs **never** committed; use env vars + `.env.example`.
- RBAC placeholder for web dashboard; audit logs for run deletions/exports.
- Webhooks + API versioning strategy in `/docs/api.md`.

## H. Quantum/Quantum-Inspired Module

- Quantum components **optional** and behind an interface:
  - **Sampler** interface for stochastic processes
  - **Optimizer** interface for parameter search / calibration
- Provide local classical fallback.
- Core simulator must not depend on quantum tooling.

## Pre-Coding Checklist (Agents)

Before implementing, the agent must output:

1. **Target files** to create or modify.
2. **New or changed interfaces** (contracts, function signatures).
3. **Acceptance checks** (how to run, what to verify).

Then implement in small, reviewable increments and validate each change.
