"""
Run all benchmarks: compute G_dyn, G_perc, G_perf proxies.
Outputs JSON report with success rate + G_perf proxy.
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def compute_g_perf_proxy(sim_success_rate: float, real_success_rate: float | None = None) -> float:
    """
    G_perf proxy: |J_sim(π) - J_real(π)|.
    If no real data, use a proxy (e.g., assume real = 0.8 * sim for demo).
    """
    if real_success_rate is None:
        real_success_rate = sim_success_rate * 0.8  # Proxy: real is 80% of sim
    return abs(sim_success_rate - real_success_rate)


def compute_g_dyn_proxy(transition_samples_sim: list[dict], transition_samples_real: list[dict] | None = None) -> float:
    """
    G_dyn proxy: divergence between transition (s,a,s') distributions.
    Stub: if no real, return 0; else mean L2 difference in s' given same (s,a).
    """
    if not transition_samples_sim:
        return 0.0
    if transition_samples_real is None or len(transition_samples_real) == 0:
        return 0.0
    # Placeholder: mean L2 of s' positions if keys match
    n = min(len(transition_samples_sim), len(transition_samples_real))
    errors = []
    for i in range(n):
        s_sim = transition_samples_sim[i].get("s_prime", transition_samples_sim[i])
        s_real = transition_samples_real[i].get("s_prime", transition_samples_real[i])
        pos_sim = s_sim.get("base_position", s_sim.get("x", 0.0))
        pos_real = s_real.get("base_position", s_real.get("x", 0.0))
        if isinstance(pos_sim, list) and isinstance(pos_real, list):
            err = sum((a - b) ** 2 for a, b in zip(pos_sim, pos_real)) ** 0.5
        else:
            err = abs((pos_sim if isinstance(pos_sim, (int, float)) else 0) - (pos_real if isinstance(pos_real, (int, float)) else 0))
        errors.append(err)
    return sum(errors) / len(errors) if errors else 0.0


def compute_g_perc_proxy(obs_sim: list[dict], obs_real: list[dict] | None = None) -> float:
    """
    G_perc proxy: divergence between observation distributions.
    Stub: if no real, return 0; else mean absolute difference of scalar observation fields.
    """
    if not obs_sim or (obs_real is not None and len(obs_real) == 0):
        return 0.0
    if obs_real is None:
        return 0.0
    n = min(len(obs_sim), len(obs_real))
    diffs = []
    for i in range(n):
        o1 = obs_sim[i]
        o2 = obs_real[i]
        v1 = o1.get("placeholder_value", o1.get("vel_estimate", 0.0))
        v2 = o2.get("placeholder_value", o2.get("vel_estimate", 0.0))
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            diffs.append(abs(v1 - v2))
    return sum(diffs) / len(diffs) if diffs else 0.0


def run_benchmarks() -> dict[str, any]:
    """Run benchmark suite and return report."""
    logger.info("Running QERS benchmarks...")
    # Placeholder: run a few sims and compute metrics
    repo_root = Path(__file__).resolve().parents[2]
    from apps.sim.runner.qers_runner import run_qers_sim
    from pathlib import Path

    example_urdf = repo_root / "examples" / "simple_robot.urdf"
    if not example_urdf.is_file():
        logger.warning("Example URDF not found, skipping benchmarks")
        return {"error": "Example URDF not found"}

    # Run 3 sims with different configs
    runs = []
    for i, use_q in enumerate([False, False, True]):
        meta = run_qers_sim(
            urdf_path=str(example_urdf),
            steps=20,
            dt=0.01,
            seed=42 + i,
            use_q_plugin=use_q,
            runs_dir=str(repo_root / "runs"),
        )
        runs.append(meta)

    # Compute metrics
    success_rate = 1.0  # Placeholder: assume all runs succeed
    g_perf = compute_g_perf_proxy(success_rate)
    g_dyn = compute_g_dyn_proxy([])  # No transition samples collected in stub
    g_perc = compute_g_perc_proxy([])  # No obs batches in stub

    report = {
        "benchmark_version": "0.1.0",
        "runs": len(runs),
        "success_rate": success_rate,
        "g_perf_proxy": g_perf,
        "g_dyn_proxy": g_dyn,
        "g_perc_proxy": g_perc,
        "integrator": "euler",
        "timestep": 0.01,
        "step_stability_risk": None,
        "runs_detail": [
            {
                "run_id": r["run_id"],
                "metrics": r.get("metrics", {}),
            }
            for r in runs
        ],
    }

    # Save report
    report_path = repo_root / "benchmark_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info(f"Benchmark report saved to {report_path}")
    return report


if __name__ == "__main__":
    report = run_benchmarks()
    print(json.dumps(report, indent=2))
