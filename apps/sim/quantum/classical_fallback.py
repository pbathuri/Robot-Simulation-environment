"""Classical fallback for Sampler and Optimizer so core sim never depends on quantum libs."""

from typing import Any

import numpy as np

from apps.sim.quantum.interfaces import Optimizer, Sampler


class ClassicalSampler(Sampler):
    """Simple normal distribution sampler; replace with quantum amplitude estimation if needed."""

    def sample(self, params: dict[str, Any], n: int, *, seed: int | None = None) -> list[float]:
        rng = np.random.default_rng(seed)
        mu = params.get("mu", 0.0)
        sigma = params.get("sigma", 1.0)
        return rng.normal(mu, sigma, size=n).tolist()


class ClassicalOptimizer(Optimizer):
    """Random search over bounds; replace with quantum or Bayesian optimizer if needed."""

    def minimize(
        self,
        objective: callable,
        bounds: dict[str, tuple[float, float]],
        *,
        max_evals: int = 100,
        seed: int | None = None,
    ) -> dict[str, Any]:
        rng = np.random.default_rng(seed)
        best_val = float("inf")
        best_params: dict[str, float] = {}
        param_names = list(bounds.keys())
        for _ in range(max_evals):
            params = {
                k: float(rng.uniform(bounds[k][0], bounds[k][1]))
                for k in param_names
            }
            val = objective(params)
            if val < best_val:
                best_val = val
                best_params = params
        return {"params": best_params, "value": best_val}
