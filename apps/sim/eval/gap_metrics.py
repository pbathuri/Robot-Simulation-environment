"""
Gap metrics: G_dyn, G_perc, G_perf — quantify the sim-to-real gap.

Based on POMDP framework from the QERS spec:
  G_dyn:  Dynamics gap  — trajectory divergence under same actions
  G_perc: Perception gap — observation divergence under same state
  G_perf: Performance gap — task metric drop across profiles

These are the standardized evaluation metrics that determine whether
simulator improvements translate to real-world performance.
"""

from __future__ import annotations

import math
from typing import Any


def compute_g_dyn(
    reference_trajectory: list[dict[str, Any]],
    test_trajectory: list[dict[str, Any]],
    *,
    state_keys: list[str] | None = None,
) -> dict[str, Any]:
    """
    G_dyn: Dynamics gap.

    Measures trajectory divergence when the same actions are replayed
    in two different models (sim vs real, or sim vs pseudo-reality).

    Returns:
        g_dyn: normalized trajectory error (0 = identical, higher = more gap)
        per_step_errors: list of per-step L2 errors
        max_error: worst-case step error
    """
    if state_keys is None:
        state_keys = ["base_position", "joint_positions"]

    n = min(len(reference_trajectory), len(test_trajectory))
    if n == 0:
        return {"g_dyn": 0.0, "per_step_errors": [], "max_error": 0.0, "steps_compared": 0}

    per_step_errors: list[float] = []

    for i in range(n):
        ref_state = reference_trajectory[i].get("state", reference_trajectory[i])
        test_state = test_trajectory[i].get("state", test_trajectory[i])

        error = 0.0
        for key in state_keys:
            ref_val = ref_state.get(key, [0.0])
            test_val = test_state.get(key, [0.0])

            if isinstance(ref_val, (list, tuple)):
                ref_flat = _flatten(ref_val)
                test_flat = _flatten(test_val)
                for r, t in zip(ref_flat, test_flat):
                    error += (r - t) ** 2
            else:
                error += (float(ref_val) - float(test_val)) ** 2

        per_step_errors.append(math.sqrt(error))

    g_dyn = sum(per_step_errors) / n if n > 0 else 0.0

    return {
        "g_dyn": g_dyn,
        "per_step_errors": per_step_errors,
        "max_error": max(per_step_errors) if per_step_errors else 0.0,
        "steps_compared": n,
    }


def compute_g_perc(
    reference_observations: list[dict[str, Any]],
    test_observations: list[dict[str, Any]],
    *,
    sensor_keys: list[str] | None = None,
) -> dict[str, Any]:
    """
    G_perc: Perception gap.

    Measures observation divergence when two models are in the same state
    but produce different sensor readings (e.g., different noise models,
    camera rendering, LiDAR accuracy).

    Returns:
        g_perc: normalized observation error
        per_step_errors: per-step observation divergence
    """
    if sensor_keys is None:
        sensor_keys = ["imu", "camera", "lidar"]

    n = min(len(reference_observations), len(test_observations))
    if n == 0:
        return {"g_perc": 0.0, "per_step_errors": [], "steps_compared": 0}

    per_step_errors: list[float] = []

    for i in range(n):
        ref_obs = reference_observations[i]
        test_obs = test_observations[i]
        error = 0.0
        count = 0

        for key in sensor_keys:
            ref_sensor = ref_obs.get(key, {})
            test_sensor = test_obs.get(key, {})

            # Compare numeric values in sensor output
            for field_name in ref_sensor:
                if field_name not in test_sensor:
                    continue
                rv = ref_sensor[field_name]
                tv = test_sensor[field_name]

                if isinstance(rv, (int, float)) and isinstance(tv, (int, float)):
                    error += (float(rv) - float(tv)) ** 2
                    count += 1
                elif isinstance(rv, list) and isinstance(tv, list):
                    for r, t in zip(_flatten(rv), _flatten(tv)):
                        error += (r - t) ** 2
                        count += 1

        per_step_errors.append(math.sqrt(error) / max(count, 1))

    g_perc = sum(per_step_errors) / n if n > 0 else 0.0

    return {
        "g_perc": g_perc,
        "per_step_errors": per_step_errors,
        "steps_compared": n,
    }


def compute_g_perf(
    design_task_metrics: dict[str, float],
    eval_task_metrics: dict[str, float],
    *,
    metric_keys: list[str] | None = None,
    higher_is_better: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """
    G_perf: Performance gap.

    Measures task-level performance drop between design and evaluation environments.
    Uses multiple task metrics (success rate, reward, completion time, etc.).

    Returns:
        g_perf: aggregate performance gap (0 = no gap)
        per_metric_drops: individual metric drops
    """
    if metric_keys is None:
        # Only use numeric metric keys (exclude run_id, profile names, etc.)
        numeric_keys = set()
        for k, v in design_task_metrics.items():
            if isinstance(v, (int, float)) and k in eval_task_metrics and isinstance(eval_task_metrics[k], (int, float)):
                numeric_keys.add(k)
        metric_keys = list(numeric_keys)

    if higher_is_better is None:
        # Defaults: higher is better for reward/success, lower for time/error
        higher_is_better = {
            "success_rate": True,
            "cumulative_reward": True,
            "avg_step_time_ms": False,
            "total_time_s": False,
            "replay_error": False,
        }

    per_metric: list[dict[str, Any]] = []
    drops: list[float] = []

    for key in metric_keys:
        d_val = design_task_metrics.get(key)
        e_val = eval_task_metrics.get(key)
        if d_val is None or e_val is None:
            continue

        d_val = float(d_val)
        e_val = float(e_val)

        hib = higher_is_better.get(key, True)
        if hib:
            drop = d_val - e_val  # Positive = degradation
        else:
            drop = e_val - d_val  # Positive = degradation (eval worse)

        # Normalize by design value
        relative_drop = drop / abs(d_val) if d_val != 0 else 0.0

        per_metric.append({
            "metric": key,
            "design_value": d_val,
            "eval_value": e_val,
            "absolute_drop": drop,
            "relative_drop": relative_drop,
            "higher_is_better": hib,
        })
        drops.append(abs(relative_drop))

    g_perf = sum(drops) / len(drops) if drops else 0.0

    return {
        "g_perf": g_perf,
        "per_metric_drops": per_metric,
        "num_metrics": len(per_metric),
    }


def compute_all_gap_metrics(
    design_run: dict[str, Any],
    eval_run: dict[str, Any],
) -> dict[str, Any]:
    """
    Compute all three gap metrics from two run artifacts.

    Expects each run to have:
      - timeline (list of step dicts with state, observation)
      - metrics (task-level metrics dict)
    """
    design_timeline = design_run.get("timeline", [])
    eval_timeline = eval_run.get("timeline", [])

    # G_dyn from trajectories
    g_dyn_result = compute_g_dyn(
        [s.get("state", s.get("state_summary", s)) for s in design_timeline],
        [s.get("state", s.get("state_summary", s)) for s in eval_timeline],
        state_keys=["base_position", "joint_positions", "end_effector"],
    )

    # G_perc from observations
    g_perc_result = compute_g_perc(
        [s.get("observation", {}) for s in design_timeline],
        [s.get("observation", {}) for s in eval_timeline],
    )

    # G_perf from task metrics
    g_perf_result = compute_g_perf(
        design_run.get("metrics", {}),
        eval_run.get("metrics", {}),
    )

    return {
        "g_dyn": g_dyn_result,
        "g_perc": g_perc_result,
        "g_perf": g_perf_result,
        "summary": {
            "g_dyn": g_dyn_result["g_dyn"],
            "g_perc": g_perc_result["g_perc"],
            "g_perf": g_perf_result["g_perf"],
        },
    }


def _flatten(val: Any) -> list[float]:
    """Flatten nested lists to a flat list of floats."""
    if isinstance(val, (int, float)):
        return [float(val)]
    if isinstance(val, (list, tuple)):
        result = []
        for item in val:
            result.extend(_flatten(item))
        return result
    return [0.0]
