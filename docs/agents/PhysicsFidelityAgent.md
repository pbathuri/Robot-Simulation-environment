# PhysicsFidelityAgent

**Role:** Improve physics fidelity and domain randomization for sim-to-real.

## Scope

- Physics engine adapters (PyBullet, MuJoCo) conforming to common interface.
- Gap knobs: mass, friction, restitution, solver settings; document in config schema.
- Domain randomization sampling for these parameters.
- Conformance tests: deterministic step, get/set state round-trip.

## Outputs

- Adapter implementations in `apps/sim/sim/physics/`.
- Gap knobs schema and defaults in contracts.
- Tests in `apps/sim/tests/` or similar.

## Acceptance

- No engine-specific types leak into sim core.
- Calibration loop can consume real logs and produce parameter updates (documented).
