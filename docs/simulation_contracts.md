# Simulation Contracts

## Purpose

All data crossing bounded contexts (sim-core ↔ physics, sim ↔ API, API ↔ web) is defined by **versioned contracts**. Schemas live in `/contracts`; we generate Python (Pydantic) and TypeScript types so both sides stay in sync.

## Contract Layout

```
contracts/
  v1/
    run.json          # Run metadata, config summary, seeds
    step.json         # Single step: state, observation, action
    replay_bundle.json # Full replay: config + actions + seeds
    metrics.json      # Eval metrics: SRCC, replay_error, task_*
    gap_knobs.json    # Domain randomization parameters
  README.md           # How to generate types
```

## Key Types (Conceptual)

- **Run:** `run_id`, `status`, `created_at`, `config_snapshot`, `seeds`, `git_hash`, `asset_versions`, `metrics_summary`.
- **Step:** `t`, `state`, `observation`, `action`, `reward` (optional).
- **ReplayBundle:** `run_id`, `config`, `seeds`, `actions[]`, `initial_state`; sufficient to re-run deterministically.
- **Metrics:** `srcc`, `replay_error`, `task_success_rate`, `cumulative_reward`, `perception_*` (placeholders).
- **GapKnobs:** Nested structure for physics (mass, friction, restitution), sensors (noise, latency, gain), actuation (delay, jitter), etc.

## Determinism & Seeds

- **Deterministic mode:** Same seed + same config + same actions ⇒ same trajectory. Seeds and config are part of the contract.
- **Stochastic mode:** All randomness goes through a seeded RNG (e.g. `numpy.random.Generator`); seed is stored in run metadata.

## Code Generation

- **Python:** `datamodel-codegen` or hand-maintained Pydantic models in `apps/sim/contracts/` or `contracts/python/` that mirror JSON Schema.
- **TypeScript:** `json-schema-to-typescript` or similar to generate types for `apps/web` and API client.

See `/contracts/README.md` for exact commands.
