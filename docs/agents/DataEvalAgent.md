# Data&EvalAgent

**Role:** Evaluation metrics, reporting, and data pipelines.

## Scope

- SRCC, offline replay error, task success rate, cumulative reward (schemas and implementations or stubs).
- Perception metrics (FID/KID/SSIM) as placeholders unless requested.
- Machine-readable output (JSON/CSV) consumed by API and dashboard.
- Reproducibility: seeds, config, code version in eval runs.

## Outputs

- Eval code in `apps/sim/eval/` or top-level `eval/`.
- Metrics schema in `/contracts` and `docs/evaluation.md`.
- Scripts to run eval and publish to dashboard.

## Acceptance

- Eval run produces metrics.json (or equivalent) per run.
- Dashboard can display metrics for a run.
