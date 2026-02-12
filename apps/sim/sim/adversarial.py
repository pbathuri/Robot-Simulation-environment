"""
SAGE-like adversarial perturbation search.

Finds worst-case environment parameter settings that maximize performance
degradation of a given control policy/config. Uses random search + hill climbing
over the gap_knobs space.

References:
  - Koos et al. (2013) transferability approach
  - Ligot & Birattari (2019) pseudo-reality
  - Domain randomization literature (Scheuch 2025 survey)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
from numpy.random import Generator

logger = logging.getLogger(__name__)


@dataclass
class AdversarialResult:
    """Result of adversarial search."""
    worst_params: dict[str, float]
    worst_score: float
    best_params: dict[str, float]
    best_score: float
    history: list[dict[str, Any]]
    iterations: int
    converged: bool


@dataclass
class SearchBounds:
    """Bounds for each parameter in the adversarial search."""
    name: str
    low: float
    high: float
    default: float = 0.0


def adversarial_search(
    evaluate_fn: Callable[[dict[str, float]], float],
    bounds: list[SearchBounds],
    *,
    max_iterations: int = 50,
    population_size: int = 10,
    elite_frac: float = 0.3,
    mutation_scale: float = 0.2,
    seed: int = 42,
    minimize: bool = False,
) -> AdversarialResult:
    """
    Evolutionary adversarial search over environment parameters.

    Uses (μ+λ) evolution strategy:
    1. Sample initial population from bounds
    2. Evaluate each candidate
    3. Select elite (top fraction)
    4. Mutate elites to create next generation
    5. Track worst-case (adversarial) and best-case parameters

    Args:
        evaluate_fn: function(params_dict) -> scalar score.
            Higher = better performance (search finds params that MINIMIZE this).
        bounds: parameter bounds for search.
        minimize: if True, find params that minimize evaluate_fn (default: find worst-case = minimize).
    """
    rng = np.random.default_rng(seed)
    n_elite = max(1, int(population_size * elite_frac))

    param_names = [b.name for b in bounds]
    lows = np.array([b.low for b in bounds])
    highs = np.array([b.high for b in bounds])
    ranges = highs - lows

    # Initialize population
    population = []
    for _ in range(population_size):
        vec = lows + rng.random(len(bounds)) * ranges
        population.append(vec)

    history: list[dict[str, Any]] = []
    best_score = float('inf') if minimize else float('-inf')
    best_params_vec = population[0].copy()
    worst_score = float('-inf') if minimize else float('inf')
    worst_params_vec = population[0].copy()

    for iteration in range(max_iterations):
        # Evaluate
        scores = []
        for vec in population:
            params = {name: float(vec[i]) for i, name in enumerate(param_names)}
            try:
                score = evaluate_fn(params)
            except Exception as e:
                logger.warning("Eval failed for %s: %s", params, e)
                score = float('inf') if minimize else float('-inf')
            scores.append(score)

        # Track best and worst
        for i, score in enumerate(scores):
            if minimize:
                if score < best_score:
                    best_score = score
                    best_params_vec = population[i].copy()
                if score > worst_score:
                    worst_score = score
                    worst_params_vec = population[i].copy()
            else:
                if score > best_score:
                    best_score = score
                    best_params_vec = population[i].copy()
                if score < worst_score:
                    worst_score = score
                    worst_params_vec = population[i].copy()

        # Log
        mean_score = np.mean(scores)
        history.append({
            "iteration": iteration,
            "mean_score": float(mean_score),
            "best_score": float(best_score),
            "worst_score": float(worst_score),
            "population_size": len(population),
        })

        if iteration % 10 == 0:
            logger.info("Adversarial iter %d: mean=%.4f best=%.4f worst=%.4f",
                       iteration, mean_score, best_score, worst_score)

        # Select elites (worst-performing = adversarial direction)
        sorted_indices = np.argsort(scores)
        if not minimize:
            sorted_indices = sorted_indices  # Low score = adversarial
        else:
            sorted_indices = sorted_indices[::-1]  # High score = adversarial

        # Elites are the ones that produced worst performance (adversarial)
        elite_indices = sorted_indices[:n_elite]
        elites = [population[i].copy() for i in elite_indices]

        # Create next generation via mutation of elites
        next_pop = list(elites)  # Keep elites
        while len(next_pop) < population_size:
            parent = elites[rng.integers(0, len(elites))]
            child = parent + rng.normal(0, mutation_scale, len(bounds)) * ranges
            child = np.clip(child, lows, highs)
            next_pop.append(child)

        population = next_pop

    # Final results
    best_params = {name: float(best_params_vec[i]) for i, name in enumerate(param_names)}
    worst_params = {name: float(worst_params_vec[i]) for i, name in enumerate(param_names)}

    return AdversarialResult(
        worst_params=worst_params,
        worst_score=float(worst_score),
        best_params=best_params,
        best_score=float(best_score),
        history=history,
        iterations=max_iterations,
        converged=len(history) > 1 and abs(history[-1]["worst_score"] - history[-2]["worst_score"]) < 1e-6,
    )


def build_bounds_from_profile(profile: dict[str, Any]) -> list[SearchBounds]:
    """Extract adversarial search bounds from a reality profile's gap_knobs."""
    knobs = profile.get("gap_knobs", {})
    bounds = []

    friction_range = knobs.get("friction_range", [0.3, 0.7])
    bounds.append(SearchBounds("friction", friction_range[0], friction_range[1],
                               profile.get("physics", {}).get("friction", 0.5)))

    restitution_range = knobs.get("restitution_range", [0.0, 0.2])
    bounds.append(SearchBounds("restitution", restitution_range[0], restitution_range[1],
                               profile.get("physics", {}).get("restitution", 0.0)))

    noise_range = knobs.get("noise_scale_range", [0.005, 0.05])
    bounds.append(SearchBounds("noise_scale", noise_range[0], noise_range[1],
                               profile.get("sensors", {}).get("noise_scale", 0.01)))

    mass_scale = knobs.get("mass_scale", [0.8, 1.2])
    if isinstance(mass_scale, (list, tuple)):
        bounds.append(SearchBounds("mass_scale", mass_scale[0], mass_scale[1], 1.0))

    return bounds


def run_adversarial_evaluation(
    urdf_path: str,
    profile: dict[str, Any],
    *,
    steps: int = 50,
    seed: int = 42,
    max_iterations: int = 30,
    population_size: int = 8,
    runs_dir: str = "runs",
) -> dict[str, Any]:
    """
    Run adversarial search: find worst-case environment params for a given robot.
    Returns adversarial result + comparison to nominal.
    """
    from apps.sim.runner.qers_runner import run_qers_sim

    bounds = build_bounds_from_profile(profile)

    def evaluate(params: dict[str, float]) -> float:
        """Run sim with adversarial params, return performance score."""
        adv_profile = dict(profile)
        adv_physics = dict(adv_profile.get("physics", {}))
        adv_sensors = dict(adv_profile.get("sensors", {}))

        adv_physics["friction"] = params.get("friction", adv_physics.get("friction", 0.5))
        adv_physics["restitution"] = params.get("restitution", adv_physics.get("restitution", 0.0))
        adv_sensors["noise_scale"] = params.get("noise_scale", adv_sensors.get("noise_scale", 0.01))
        adv_profile["physics"] = adv_physics
        adv_profile["sensors"] = adv_sensors

        meta = run_qers_sim(
            urdf_path,
            steps=steps,
            dt=float(adv_physics.get("timestep", 0.01)),
            seed=seed,
            _profile_override=adv_profile,
            runs_dir=runs_dir,
        )
        # Use avg step time as proxy (lower = faster = better for sim; we want to find params
        # that cause the most deviation from nominal)
        return meta.get("metrics", {}).get("avg_step_time_ms", 0.0)

    result = adversarial_search(
        evaluate,
        bounds,
        max_iterations=max_iterations,
        population_size=population_size,
        seed=seed,
        minimize=False,  # Find params that maximize step time (worst case)
    )

    return {
        "worst_params": result.worst_params,
        "worst_score": result.worst_score,
        "best_params": result.best_params,
        "best_score": result.best_score,
        "iterations": result.iterations,
        "converged": result.converged,
        "history": result.history,
        "bounds": [{"name": b.name, "low": b.low, "high": b.high, "default": b.default} for b in bounds],
    }
