"""Quantum showcase API routes: sampling, comparison, circuit info."""
from __future__ import annotations
import math
from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/quantum", tags=["quantum"])


class SampleRequest(BaseModel):
    n: int = 1000
    distribution: str = "gaussian"
    noise_scale: float = 0.05
    state_value: float = 0.0
    velocity: float = 0.0
    num_contacts: int = 0


class CompareRequest(BaseModel):
    env_id: str = "cartpole"
    steps: int = 200
    seed: int = 42
    noise_scale: float = 0.05


@router.get("/distributions")
def list_distributions() -> dict[str, Any]:
    return {"distributions": [
        {"id": "gaussian", "name": "Gaussian", "description": "Standard normal. Most common in classical DR.", "color": "#3b82f6"},
        {"id": "laplace", "name": "Laplace", "description": "Heavy-tailed. Models sudden friction changes.", "color": "#22c55e"},
        {"id": "cauchy", "name": "Cauchy", "description": "Very heavy tails. Models rare extreme events.", "color": "#f59e0b"},
        {"id": "mixture", "name": "Mixture", "description": "85% Gaussian + 15% heavy Laplace tail. Quantum-inspired.", "color": "#a855f7"},
        {"id": "bimodal", "name": "Bimodal", "description": "Two modes (backlash snap). Unique to quantum circuits.", "color": "#ef4444"},
        {"id": "quantum", "name": "Quantum Circuit", "description": "4-qubit parameterized circuit. State-dependent, entangled.", "color": "#8b5cf6"},
    ]}


@router.post("/sample")
def sample_distribution(req: SampleRequest) -> dict[str, Any]:
    from apps.sim.sim.quantum.q_plugin import QPlugin
    plugin = QPlugin(use_quantum=False, noise_scale=req.noise_scale, seed=42, distribution=req.distribution)
    params = {"state_value": req.state_value, "velocity": req.velocity,
              "sigma": req.noise_scale, "num_contacts": req.num_contacts}
    samples = plugin.sample(params, req.n)
    import numpy as np
    arr = np.array(samples)
    # Histogram bins
    n_bins = 50
    counts, edges = np.histogram(arr, bins=n_bins)
    histogram = [{"bin_start": float(edges[i]), "bin_end": float(edges[i + 1]),
                  "count": int(counts[i])} for i in range(n_bins)]
    return {
        "distribution": req.distribution,
        "n": req.n,
        "samples": samples[:200],  # first 200 for plotting
        "stats": {"mean": float(arr.mean()), "std": float(arr.std()),
                  "min": float(arr.min()), "max": float(arr.max()),
                  "kurtosis": float(((arr - arr.mean()) ** 4).mean() / arr.std() ** 4 - 3) if arr.std() > 0 else 0},
        "histogram": histogram,
    }


@router.post("/compare")
def compare_noise_modes(req: CompareRequest) -> dict[str, Any]:
    """Run same env with deterministic, classical gaussian, and quantum noise. Return overlaid results."""
    from apps.sim.envs.registry import run_episode
    modes = [
        {"noise_scale": 0.0, "noise_type": "gaussian", "label": "Deterministic", "color": "#6b7280"},
        {"noise_scale": req.noise_scale, "noise_type": "gaussian", "label": "Classical Gaussian", "color": "#3b82f6"},
        {"noise_scale": req.noise_scale, "noise_type": "quantum", "label": "Quantum Mixture", "color": "#a855f7"},
    ]
    results = []
    for mode in modes:
        ep = run_episode(req.env_id, steps=req.steps, seed=req.seed,
                         noise_scale=mode["noise_scale"], noise_type=mode["noise_type"])
        rewards = [t["reward"] for t in ep["trajectory"]]
        cum_rewards = []
        s = 0.0
        for r in rewards:
            s += r
            cum_rewards.append(s)
        results.append({
            "label": mode["label"],
            "color": mode["color"],
            "noise_type": mode["noise_type"],
            "total_reward": ep["total_reward"],
            "steps_run": ep["steps_run"],
            "rewards": rewards,
            "cumulative_rewards": cum_rewards,
        })
    return {"env_id": req.env_id, "seed": req.seed, "results": results}


@router.get("/circuit")
def get_circuit_info() -> dict[str, Any]:
    """Return quantum circuit description for visualization."""
    return {
        "num_qubits": 4,
        "description": "Parameterized 4-qubit circuit for state-dependent noise sampling",
        "gates": [
            {"type": "RY", "qubit": 0, "param": "theta_state", "label": "Encode joint angle"},
            {"type": "RY", "qubit": 1, "param": "theta_velocity", "label": "Encode joint velocity"},
            {"type": "CNOT", "control": 0, "target": 1, "label": "Entangle state+velocity"},
            {"type": "CNOT", "control": 1, "target": 2, "label": "Propagate entanglement"},
            {"type": "RZ", "qubit": 2, "param": "theta_state + theta_velocity", "label": "Phase encoding"},
            {"type": "CNOT", "control": 2, "target": 3, "label": "Full entanglement"},
            {"type": "H", "qubit": 3, "label": "Superposition for randomness"},
        ],
        "measurements": "All qubits measured in computational basis",
        "output": "16 possible outcomes mapped to [-1, 1] noise range, scaled by sigma",
        "advantage": "Entangled qubits produce correlated noise across joints -- physically motivated by coupled mechanical systems. Classical i.i.d. sampling cannot capture these correlations without explicit modeling.",
        "ascii_diagram": (
            "q0: ──RY(θ_s)──●──────────────────────────\n"
            "                │                          \n"
            "q1: ──RY(θ_v)──X──●───────────────────────\n"
            "                   │                       \n"
            "q2: ──────────────X──RZ(θ_s+θ_v)──●───────\n"
            "                                   │       \n"
            "q3: ──────────────────────────────X──H──M──\n"
        ),
    }
