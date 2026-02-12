"""
Residual model training pipeline (numpy-based, no PyTorch dependency).

Collects paired (sim_state, real_state) data from running the same actions
in two models (design and pseudo-reality), then trains a small MLP to predict
delta = pseudo_real_state - sim_state.

This implements the NAS (Neural-Augmented Simulation) concept from Golemo et al. (2018).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def collect_paired_data(
    urdf_path: str,
    design_profile_id: str,
    eval_profile_id: str,
    *,
    episodes: int = 10,
    steps_per_episode: int = 50,
    seed: int = 42,
    runs_dir: str = "runs",
) -> dict[str, Any]:
    """
    Collect paired (sim_state, pseudo_real_state) data by running the same
    actions in design and eval profiles.

    Returns:
        {
            "state_pairs": [(sim_state_vec, real_state_vec), ...],
            "action_pairs": [(action_vec), ...],
            "episodes": int,
            "total_pairs": int,
        }
    """
    from apps.sim.runner.qers_runner import run_qers_sim
    from apps.sim.profiles.loader import load_profile

    design_profile = load_profile(design_profile_id) or {}
    eval_profile = load_profile(eval_profile_id) or {}

    all_sim_states: list[list[float]] = []
    all_real_states: list[list[float]] = []
    all_actions: list[list[float]] = []

    for ep in range(episodes):
        ep_seed = seed + ep

        # Run in design model
        design_meta = run_qers_sim(
            urdf_path, steps=steps_per_episode, seed=ep_seed,
            reality_profile=design_profile_id, runs_dir=runs_dir,
        )
        # Run same seed in eval model (same actions due to same seed)
        eval_meta = run_qers_sim(
            urdf_path, steps=steps_per_episode, seed=ep_seed,
            reality_profile=eval_profile_id, runs_dir=runs_dir,
        )

        # Load replay data
        design_replay = _load_json(Path(runs_dir) / design_meta["run_id"] / "replay.json")
        eval_replay = _load_json(Path(runs_dir) / eval_meta["run_id"] / "replay.json")

        if design_replay and eval_replay:
            d_actions = design_replay.get("actions", [])
            # Extract state vectors from timeline in reports
            d_report = _load_json(Path(runs_dir) / design_meta["run_id"] / "report.json")
            e_report = _load_json(Path(runs_dir) / eval_meta["run_id"] / "report.json")

            if d_report and e_report:
                d_timeline = d_report.get("timeline_summary", [])
                e_timeline = e_report.get("timeline_summary", [])

                for t_d, t_e in zip(d_timeline, e_timeline):
                    sim_pos = t_d.get("state_summary", {}).get("base_pos", [0.0, 0.0])
                    real_pos = t_e.get("state_summary", {}).get("base_pos", [0.0, 0.0])
                    all_sim_states.append(sim_pos)
                    all_real_states.append(real_pos)
                    all_actions.append([0.0])  # Placeholder action

    return {
        "sim_states": all_sim_states,
        "real_states": all_real_states,
        "actions": all_actions,
        "episodes": episodes,
        "total_pairs": len(all_sim_states),
    }


def train_residual_mlp(
    sim_states: list[list[float]],
    real_states: list[list[float]],
    actions: list[list[float]],
    *,
    hidden_dim: int = 64,
    learning_rate: float = 0.001,
    epochs: int = 200,
    batch_size: int = 32,
    seed: int = 42,
) -> dict[str, Any]:
    """
    Train a small MLP to predict residual: delta = real_state - sim_state.

    Input: [sim_state, action]
    Output: delta (same dim as sim_state)

    Returns:
        weights dict compatible with LearnedResidualModel.
    """
    rng = np.random.default_rng(seed)

    # Build data arrays
    X_sim = np.array(sim_states, dtype=np.float64)
    X_real = np.array(real_states, dtype=np.float64)
    X_act = np.array(actions, dtype=np.float64)

    # Target: delta = real - sim
    Y = X_real - X_sim

    # Input: concat sim_state + action
    X = np.hstack([X_sim, X_act])

    n_samples = X.shape[0]
    input_dim = X.shape[1]
    output_dim = Y.shape[1]

    if n_samples == 0:
        logger.warning("No training data, returning zero weights")
        from apps.sim.sim.residual.learned import LearnedResidualModel
        return LearnedResidualModel.create_random_weights(output_dim, X_act.shape[1], hidden_dim, seed)

    # Initialize weights (Xavier-like)
    scale1 = np.sqrt(2.0 / input_dim)
    w1 = rng.normal(0, scale1, (hidden_dim, input_dim))
    b1 = np.zeros(hidden_dim)
    scale2 = np.sqrt(2.0 / hidden_dim)
    w2 = rng.normal(0, scale2, (hidden_dim, hidden_dim))
    b2 = np.zeros(hidden_dim)
    scale3 = np.sqrt(2.0 / hidden_dim)
    w3 = rng.normal(0, scale3, (output_dim, hidden_dim))
    b3 = np.zeros(output_dim)

    # Training loop (mini-batch SGD with momentum)
    best_loss = float('inf')
    losses: list[float] = []

    # Momentum
    mw1 = np.zeros_like(w1); mb1 = np.zeros_like(b1)
    mw2 = np.zeros_like(w2); mb2 = np.zeros_like(b2)
    mw3 = np.zeros_like(w3); mb3 = np.zeros_like(b3)
    momentum = 0.9

    for epoch in range(epochs):
        # Shuffle
        perm = rng.permutation(n_samples)
        X_shuf = X[perm]
        Y_shuf = Y[perm]

        epoch_loss = 0.0
        n_batches = 0

        for start in range(0, n_samples, batch_size):
            end = min(start + batch_size, n_samples)
            X_batch = X_shuf[start:end]
            Y_batch = Y_shuf[start:end]
            bs = X_batch.shape[0]

            # Forward
            z1 = X_batch @ w1.T + b1          # (bs, hidden)
            h1 = np.tanh(z1)
            z2 = h1 @ w2.T + b2               # (bs, hidden)
            h2 = np.tanh(z2)
            y_pred = h2 @ w3.T + b3            # (bs, output)

            # Loss (MSE)
            diff = y_pred - Y_batch
            loss = np.mean(diff ** 2)
            epoch_loss += loss * bs
            n_batches += 1

            # Backward
            d_out = 2.0 * diff / bs            # (bs, output)
            dw3 = d_out.T @ h2                 # (output, hidden)
            db3 = d_out.sum(axis=0)

            d_h2 = d_out @ w3                  # (bs, hidden)
            d_z2 = d_h2 * (1.0 - h2 ** 2)     # tanh derivative
            dw2 = d_z2.T @ h1
            db2 = d_z2.sum(axis=0)

            d_h1 = d_z2 @ w2
            d_z1 = d_h1 * (1.0 - h1 ** 2)
            dw1 = d_z1.T @ X_batch
            db1 = d_z1.sum(axis=0)

            # Update with momentum
            mw1 = momentum * mw1 - learning_rate * dw1; w1 += mw1
            mb1 = momentum * mb1 - learning_rate * db1; b1 += mb1
            mw2 = momentum * mw2 - learning_rate * dw2; w2 += mw2
            mb2 = momentum * mb2 - learning_rate * db2; b2 += mb2
            mw3 = momentum * mw3 - learning_rate * dw3; w3 += mw3
            mb3 = momentum * mb3 - learning_rate * db3; b3 += mb3

        avg_loss = epoch_loss / n_samples if n_samples > 0 else 0.0
        losses.append(avg_loss)
        if avg_loss < best_loss:
            best_loss = avg_loss

        if epoch % 50 == 0:
            logger.info("Epoch %d/%d  loss=%.6f", epoch, epochs, avg_loss)

    weights = {
        "w1": w1, "b1": b1,
        "w2": w2, "b2": b2,
        "w3": w3, "b3": b3,
    }

    return {
        "weights": weights,
        "training_loss": losses,
        "best_loss": best_loss,
        "epochs": epochs,
        "input_dim": input_dim,
        "output_dim": output_dim,
        "hidden_dim": hidden_dim,
    }


def save_residual_model(
    weights: dict[str, Any],
    output_path: str | Path,
    *,
    state_keys: list[str] | None = None,
    action_keys: list[str] | None = None,
) -> str:
    """Save trained residual model weights to .npz file."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    save_dict = dict(weights)
    if state_keys:
        save_dict["state_keys"] = np.array(state_keys)
    if action_keys:
        save_dict["action_keys"] = np.array(action_keys)

    np.savez(str(p), **save_dict)
    logger.info("Saved residual model to %s", p)
    return str(p)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with open(path) as f:
        return json.load(f)
