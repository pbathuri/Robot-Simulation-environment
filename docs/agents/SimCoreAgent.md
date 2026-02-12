# SimCoreAgent

**Role:** Design and implement simulation core behavior: stepping, state/obs/action separation, plugin interfaces.

## Scope

- Deterministic `step(dt)` and stochastic `step_stochastic(dt, rng)` with explicit seed control.
- POMDP-like separation of state, observation, action; definitions live in contracts.
- Time-step integrator abstraction; single responsibility per module.
- Physics and sensor plugins behind interfaces; no engine-specific code in core.

## Outputs

- Code in `apps/sim/sim/` (core, physics base, sensors base).
- Contract updates in `/contracts` and Pydantic models in `apps/sim/contracts/`.
- Unit tests for determinism and state round-trip.

## Acceptance

- Running a scenario with fixed seed produces identical replay bundle on re-run.
- Conformance tests for any new physics adapter pass.
