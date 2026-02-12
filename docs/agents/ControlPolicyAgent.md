# ControlPolicyAgent

**Role:** Low-level control and high-level policy interfaces.

## Scope

- Clear separation: low-level control (e.g. joint targets, PID) vs policy (task-level actions).
- Action space explicit in contracts (dimensions, bounds, discrete/continuous).
- Smoothness and regularization hooks (action rate limits, filters) for sim-to-real.

## Outputs

- Control and policy modules in `apps/sim/sim/control/` and/or `ml/`.
- Action schema and examples in contracts.
- Tests that policy produces valid actions for given observations.

## Acceptance

- Policy depends only on observations and config; no direct physics access.
- Action space documented and validated at boundaries.
