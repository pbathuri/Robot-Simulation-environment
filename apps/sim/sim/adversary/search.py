"""
AdversarySearch: sample params (friction, mass, noise); run sim; compute G_perf proxy; return worst-case set.
SAGE-like: find parameter sets that maximize performance drop for robust training.
"""

from pathlib import Path
from typing import Any, Callable

import numpy as np


def default_g_perf_proxy(sim_success_rate: float, real_success_rate: float | None = None) -> float:
    """|J_sim - J_real|; if no real, use proxy real = 0.8 * sim."""
    if real_success_rate is None:
        real_success_rate = sim_success_rate * 0.8
    return abs(sim_success_rate - real_success_rate)


class AdversarySearch:
    """
    Sample params from bounds; run sim (or use provided run_fn); compute G_perf; return worst-case params.
    """

    def __init__(
        self,
        param_bounds: dict[str, tuple[float, float]],
        *,
        n_samples: int = 10,
        seed: int | None = None,
    ) -> None:
        self.param_bounds = param_bounds
        self.n_samples = n_samples
        self._rng = np.random.default_rng(seed)

    def run(
        self,
        run_fn: Callable[[dict[str, float]], dict[str, Any]],
        g_perf_fn: Callable[[dict[str, Any]], float] | None = None,
    ) -> dict[str, Any]:
        """
        run_fn(params) -> run result (must contain or allow computing success/reward).
        g_perf_fn(result) -> G_perf value (higher = worse for sim). Default: use result.get("metrics", {}).get("task_success_rate") and proxy.
        Returns: { "worst_params": {...}, "worst_g_perf": float, "all_results": [...] }.
        """
        results: list[tuple[dict[str, float], dict[str, Any], float]] = []
        for _ in range(self.n_samples):
            params = {
                k: float(self._rng.uniform(b[0], b[1]))
                for k, b in self.param_bounds.items()
            }
            run_result = run_fn(params)
            if g_perf_fn is not None:
                g_perf = g_perf_fn(run_result)
            else:
                metrics = run_result.get("metrics", {})
                task_sr = metrics.get("task_success_rate")
                if task_sr is None:
                    task_sr = 1.0  # Assume success if not present
                g_perf = default_g_perf_proxy(float(task_sr))
            results.append((params, run_result, g_perf))
        # Worst case = max G_perf
        results.sort(key=lambda x: x[2], reverse=True)
        worst_params, worst_run, worst_g_perf = results[0]
        return {
            "worst_params": worst_params,
            "worst_g_perf": worst_g_perf,
            "all_results": [
                {"params": p, "g_perf": g} for p, _, g in results
            ],
        }
