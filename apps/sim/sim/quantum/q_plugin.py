"""
Q-Plugin: Quantum-stochastic layer for sim-to-real gap modeling.

Phase 4 full implementation:
  - Multiple noise distributions: Gaussian, Laplace, Cauchy, mixture
  - State-dependent noise scaling (velocity, contact, joint limits)
  - Contact-aware "friction collapse" perturbations
  - Per-joint noise profiles
  - Configurable via reality profile gap_knobs
  - Quantum circuit path (Qiskit) + classical fallback

Concept: The Q-Plugin intercepts (s_t, a_t, engine_diagnostics) after each
physics step and applies stochastic perturbations that model real-world
micro-stochasticity (backlash, friction, sensor drift, etc.).
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Any

import numpy as np
from numpy.random import Generator

try:
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

from apps.sim.quantum.interfaces import Sampler


class NoiseDistribution(str, Enum):
    GAUSSIAN = "gaussian"
    LAPLACE = "laplace"
    CAUCHY = "cauchy"
    UNIFORM = "uniform"
    MIXTURE = "mixture"       # Gaussian + heavy tail
    BIMODAL = "bimodal"       # Two-mode (e.g. backlash snap)


class QPlugin(Sampler):
    """
    Quantum-stochastic perturbation sampler (Phase 4).

    Supports configurable noise distributions, state-dependent scaling,
    per-joint profiles, and contact-aware perturbations.
    """

    def __init__(
        self,
        *,
        use_quantum: bool = True,
        noise_scale: float = 0.01,
        seed: int | None = None,
        distribution: str = "gaussian",
        # State-dependent scaling coefficients
        velocity_coupling: float = 0.1,    # noise scales with joint velocity
        contact_coupling: float = 0.05,    # noise scales with contact count
        joint_limit_coupling: float = 0.2, # noise increases near joint limits
        # Mixture params (if distribution == "mixture")
        heavy_tail_weight: float = 0.15,   # probability of heavy-tail sample
        heavy_tail_scale: float = 3.0,     # scale multiplier for heavy-tail
        # Per-joint overrides
        per_joint_scales: list[float] | None = None,
        # Backlash simulation
        backlash_deadband: float = 0.0,    # deadband in radians
    ) -> None:
        self.use_quantum = use_quantum and QISKIT_AVAILABLE
        self.noise_scale = noise_scale
        self.distribution = NoiseDistribution(distribution)
        self.velocity_coupling = velocity_coupling
        self.contact_coupling = contact_coupling
        self.joint_limit_coupling = joint_limit_coupling
        self.heavy_tail_weight = heavy_tail_weight
        self.heavy_tail_scale = heavy_tail_scale
        self.per_joint_scales = per_joint_scales
        self.backlash_deadband = backlash_deadband
        self._rng: Generator = np.random.default_rng(seed)
        self._prev_joint_targets: list[float] | None = None  # for backlash

    @classmethod
    def from_profile(cls, profile: dict[str, Any], *, seed: int | None = None) -> QPlugin:
        """Build QPlugin from a reality profile's gap_knobs."""
        knobs = profile.get("gap_knobs", {})
        q_cfg = knobs.get("q_plugin", {})
        return cls(
            use_quantum=q_cfg.get("use_quantum", False),
            noise_scale=float(knobs.get("noise_scale", profile.get("sensors", {}).get("noise_scale", 0.01))),
            seed=seed,
            distribution=q_cfg.get("distribution", "gaussian"),
            velocity_coupling=float(q_cfg.get("velocity_coupling", 0.1)),
            contact_coupling=float(q_cfg.get("contact_coupling", 0.05)),
            joint_limit_coupling=float(q_cfg.get("joint_limit_coupling", 0.2)),
            heavy_tail_weight=float(q_cfg.get("heavy_tail_weight", 0.15)),
            heavy_tail_scale=float(q_cfg.get("heavy_tail_scale", 3.0)),
            per_joint_scales=q_cfg.get("per_joint_scales"),
            backlash_deadband=float(q_cfg.get("backlash_deadband", 0.0)),
        )

    # ── Core sampling ──────────────────────────────────────────────────────

    def sample(
        self,
        params: dict[str, Any],
        n: int,
        *,
        seed: int | None = None,
    ) -> list[float]:
        """Sample n perturbations with state-dependent scaling."""
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        sigma = self._effective_sigma(params)

        if self.use_quantum:
            return self._sample_quantum(params, n, sigma)
        return self._sample_classical(n, sigma)

    def _effective_sigma(self, params: dict[str, Any]) -> float:
        """Compute effective noise scale from state and diagnostics."""
        base = params.get("sigma", self.noise_scale)
        state_val = params.get("state_value", 0.0)
        velocity = params.get("velocity", 0.0)
        num_contacts = params.get("num_contacts", 0)
        joint_limit_proximity = params.get("joint_limit_proximity", 0.0)  # 0..1

        sigma = base
        sigma *= (1.0 + self.velocity_coupling * abs(velocity))
        sigma *= (1.0 + self.contact_coupling * num_contacts)
        sigma *= (1.0 + self.joint_limit_coupling * joint_limit_proximity)
        return max(sigma, 1e-8)

    def _sample_classical(self, n: int, sigma: float) -> list[float]:
        """Classical sampling with configurable distribution."""
        dist = self.distribution

        if dist == NoiseDistribution.GAUSSIAN:
            return self._rng.normal(0, sigma, n).tolist()

        elif dist == NoiseDistribution.LAPLACE:
            return self._rng.laplace(0, sigma / math.sqrt(2), n).tolist()

        elif dist == NoiseDistribution.CAUCHY:
            return (sigma * self._rng.standard_cauchy(n)).tolist()

        elif dist == NoiseDistribution.UNIFORM:
            return self._rng.uniform(-sigma * math.sqrt(3), sigma * math.sqrt(3), n).tolist()

        elif dist == NoiseDistribution.MIXTURE:
            samples = []
            for _ in range(n):
                if self._rng.random() < self.heavy_tail_weight:
                    samples.append(float(self._rng.laplace(0, sigma * self.heavy_tail_scale / math.sqrt(2))))
                else:
                    samples.append(float(self._rng.normal(0, sigma)))
            return samples

        elif dist == NoiseDistribution.BIMODAL:
            # Bimodal: snap to ±offset with noise (models backlash snap)
            offset = sigma * 2.0
            samples = []
            for _ in range(n):
                mode = offset if self._rng.random() > 0.5 else -offset
                samples.append(mode + float(self._rng.normal(0, sigma * 0.3)))
            return samples

        return self._rng.normal(0, sigma, n).tolist()

    def _sample_quantum(self, params: dict[str, Any], n: int, sigma: float) -> list[float]:
        """Quantum circuit path: encode state into rotation → measure → scale."""
        state_val = params.get("state_value", 0.0)
        velocity = params.get("velocity", 0.0)

        num_qubits = 4
        qc = QuantumCircuit(num_qubits)

        # Encode state and velocity into rotations
        angle_state = float(state_val) * math.pi / 4.0
        angle_vel = float(velocity) * math.pi / 4.0
        qc.ry(angle_state, 0)
        qc.ry(angle_vel, 1)
        # Entangle
        qc.cx(0, 1)
        qc.cx(1, 2)
        qc.rz(angle_state + angle_vel, 2)
        qc.cx(2, 3)
        qc.h(3)  # Add superposition for randomness

        # Get statevector probabilities
        sv = Statevector.from_instruction(qc)
        probs = sv.probabilities()

        # Sample from distribution
        max_val = 2**num_qubits - 1
        indices = self._rng.choice(len(probs), size=n, p=probs)
        samples = []
        for idx in indices:
            normalized = (idx / max_val - 0.5) * 2.0  # [-1, 1]
            samples.append(normalized * sigma)
        return samples

    # ── State perturbation ─────────────────────────────────────────────────

    def perturb_state(
        self,
        state: dict[str, Any],
        action: dict[str, Any],
        diagnostics: dict[str, Any],
        *,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """
        Intercept (s_t, a_t, diagnostics) → return perturbed state.
        Applies per-joint noise, backlash simulation, and contact-aware scaling.
        """
        perturbed = dict(state)
        joint_positions = list(state.get("joint_positions", []))
        joint_velocities = list(state.get("joint_velocities", []))
        num_contacts = diagnostics.get("num_contacts", 0)

        if not joint_positions:
            return perturbed

        n_joints = len(joint_positions)

        # Per-joint perturbations
        for j in range(n_joints):
            vel_j = joint_velocities[j] if j < len(joint_velocities) else 0.0
            pos_j = joint_positions[j]

            # Joint limit proximity (assume ±π range)
            limit_prox = min(abs(pos_j) / math.pi, 1.0)

            # Per-joint scale override
            base_scale = self.noise_scale
            if self.per_joint_scales and j < len(self.per_joint_scales):
                base_scale *= self.per_joint_scales[j]

            params = {
                "state_value": float(pos_j),
                "velocity": float(vel_j),
                "sigma": base_scale,
                "num_contacts": num_contacts,
                "joint_limit_proximity": limit_prox,
            }
            perturbation = self.sample(params, 1, seed=seed)[0] if seed else self.sample(params, 1)[0]

            # Backlash simulation
            backlash_offset = 0.0
            if self.backlash_deadband > 0:
                targets = action.get("joint_targets", [])
                if self._prev_joint_targets and j < len(targets) and j < len(self._prev_joint_targets):
                    direction_change = (targets[j] - self._prev_joint_targets[j])
                    if abs(direction_change) > 0:
                        backlash_offset = math.copysign(
                            min(self.backlash_deadband, abs(direction_change) * 0.5),
                            direction_change
                        )

            joint_positions[j] = pos_j + perturbation + backlash_offset

        # Also perturb velocities slightly
        if joint_velocities:
            vel_perturbations = self._sample_classical(len(joint_velocities), self.noise_scale * 0.5)
            joint_velocities = [v + dv for v, dv in zip(joint_velocities, vel_perturbations)]
            perturbed["joint_velocities"] = joint_velocities

        perturbed["joint_positions"] = joint_positions

        # Store targets for backlash tracking
        targets = action.get("joint_targets")
        if targets:
            self._prev_joint_targets = list(targets)

        return perturbed

    def get_config(self) -> dict[str, Any]:
        """Return current configuration as serializable dict."""
        return {
            "use_quantum": self.use_quantum,
            "noise_scale": self.noise_scale,
            "distribution": self.distribution.value,
            "velocity_coupling": self.velocity_coupling,
            "contact_coupling": self.contact_coupling,
            "joint_limit_coupling": self.joint_limit_coupling,
            "heavy_tail_weight": self.heavy_tail_weight,
            "heavy_tail_scale": self.heavy_tail_scale,
            "backlash_deadband": self.backlash_deadband,
            "per_joint_scales": self.per_joint_scales,
        }


class ClassicalFallback(Sampler):
    """Classical fallback for QPlugin when quantum unavailable."""

    def __init__(self, noise_scale: float = 0.01, seed: int | None = None) -> None:
        self.noise_scale = noise_scale
        self._rng = np.random.default_rng(seed)

    def sample(
        self,
        params: dict[str, Any],
        n: int,
        *,
        seed: int | None = None,
    ) -> list[float]:
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        mu = params.get("mu", 0.0)
        sigma = params.get("sigma", self.noise_scale)
        return self._rng.normal(mu, sigma, size=n).tolist()
