# Evaluation

## Metrics (Placeholders + Schemas)

All metrics use versioned schemas; output is machine-readable and consumed by the dashboard.

### SRCC (Sim-to-Real Correlation Coefficient)

- **Definition:** Pearson correlation between simulation performance and real-world performance across policies (or random seeds / DR samples).
- **Use:** High SRCC ⇒ sim improvements translate to reality; low SRCC ⇒ large reality gap.

For research context (pseudo-reality, multi-profile evaluation, gap visualization), see **`docs/research_context_and_next_phase.md`**.
- **Schema:** `metrics.srcc` (float or null), optional `srcc_confidence_interval`.

### Offline Replay Error

- **Definition:** Execute real robot trajectories (actions) in simulation open-loop; measure state deviation (e.g. position/velocity error over time).
- **Use:** Large error ⇒ missing dynamics or sensor/actuation modeling.
- **Schema:** `metrics.replay_error` (e.g. mean L2, max error, per-step), `replay_error_units`.

### Task Metrics

- **Success rate:** Percentage of runs that meet task success criteria.
- **Cumulative reward:** Sum of rewards per episode (when reward is defined).
- **Schema:** `metrics.task_success_rate`, `metrics.cumulative_reward`, optional `metrics.episode_lengths`.

### Perception Metrics (Placeholders)

- **FID/KID/SSIM:** Placeholders for vision realism (sim vs real images). Not fully implemented unless requested.
- **Schema:** `metrics.fid`, `metrics.kid`, `metrics.ssim` (optional, nullable).

## Report Format

- **Per run:** JSON file under `runs/<run_id>/metrics.json` with the above fields.
- **Aggregated:** CSV or JSON for batch comparisons (e.g. SRCC across many runs).
- **Dashboard:** API serves metrics by `run_id`; web displays in run detail and charts placeholder.

## Reproducibility

Every eval run records:

- Seed(s)
- Config (or config hash)
- Code version (git hash)
- Timestamp

So that results can be reproduced. See also `docs/simulation_contracts.md` for `metrics.json` schema.
