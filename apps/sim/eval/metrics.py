"""
Evaluation metrics: SRCC, replay error, task metrics (placeholders + schemas).
Output is machine-readable and conforms to contracts/v1/metrics.json.
"""

from pathlib import Path
from typing import Any

from apps.sim.contracts.metrics import MetricsPayload


def compute_srcc_placeholder(
    sim_success_rates: list[float],
    real_success_rates: list[float],
) -> float | None:
    """
    SRCC: Pearson correlation between sim and real success rates across policies/runs.
    Placeholder: returns None if lists length mismatch or empty; else computes correlation.
    """
    if len(sim_success_rates) != len(real_success_rates) or len(sim_success_rates) < 2:
        return None
    n = len(sim_success_rates)
    mean_s = sum(sim_success_rates) / n
    mean_r = sum(real_success_rates) / n
    cov = sum((s - mean_s) * (r - mean_r) for s, r in zip(sim_success_rates, real_success_rates)) / n
    var_s = sum((s - mean_s) ** 2 for s in sim_success_rates) / n
    var_r = sum((r - mean_r) ** 2 for r in real_success_rates) / n
    if var_s * var_r <= 0:
        return None
    return cov / (var_s * var_r) ** 0.5


def compute_replay_error_placeholder(
    real_actions: list[dict[str, Any]],
    sim_states_after_replay: list[dict[str, Any]],
    reference_states: list[dict[str, Any]] | None = None,
) -> float | None:
    """
    Offline replay error: run real actions in sim, compare resulting states to reference.
    Placeholder: if reference_states given, return mean L2 position error; else return 0.0.
    """
    if reference_states is None or len(sim_states_after_replay) != len(reference_states):
        return None
    errors = []
    for sim_s, ref_s in zip(sim_states_after_replay, reference_states):
        x_s = sim_s.get("x", 0.0)
        x_r = ref_s.get("x", 0.0)
        errors.append((x_s - x_r) ** 2)
    if not errors:
        return None
    return (sum(errors) / len(errors)) ** 0.5


def compute_metrics_placeholder(
    run_id: str,
    run_dir: Path | str,
    *,
    task_success_rate: float | None = None,
    cumulative_reward: float | None = None,
) -> MetricsPayload:
    """
    Build metrics payload for a run. Writes metrics.json into run_dir.
    SRCC and replay_error require batch/real data; here we only fill task/reward placeholders.
    """
    run_dir = Path(run_dir)
    payload = MetricsPayload(
        run_id=run_id,
        srcc=None,
        replay_error=None,
        replay_error_units="m",
        task_success_rate=task_success_rate,
        cumulative_reward=cumulative_reward,
        fid=None,
        kid=None,
        ssim=None,
    )
    metrics_path = run_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        f.write(payload.model_dump_json(indent=2))
    return payload
