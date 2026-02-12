"""Eval: SRCC, replay error, task metrics, batch evaluation, reporting."""

from apps.sim.eval.metrics import compute_metrics_placeholder, compute_replay_error_placeholder, compute_srcc_placeholder
from apps.sim.eval.batch_eval import (
    compute_replay_error,
    compute_performance_drop,
    compute_rank_stability,
    compute_gap_width,
    evaluate_batch_report,
)

__all__ = [
    "compute_metrics_placeholder",
    "compute_replay_error_placeholder",
    "compute_srcc_placeholder",
    "compute_replay_error",
    "compute_performance_drop",
    "compute_rank_stability",
    "compute_gap_width",
    "evaluate_batch_report",
]
