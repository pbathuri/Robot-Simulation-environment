# PerceptionAgent

**Role:** Sensor models and perception stack for sim and sim-to-real.

## Scope

- Sensor models (camera, LiDAR, IMU) with noise, latency, and DR knobs.
- Observations conform to contracts; sim core uses only observation schema.
- Placeholders for perception metrics (FID/KID/SSIM) when evaluating vision.

## Outputs

- Sensor implementations in `apps/sim/sim/sensors/`.
- Config schema for noise and DR per sensor.
- Documentation of observation schema in `docs/simulation_contracts.md`.

## Acceptance

- Deterministic mode (rng=None) yields identical observations for same state.
- Latency and noise are configurable via gap knobs.
