"""
Enhanced SimCore with Q-Plugin integration and domain randomization.

Supports:
  - step(): deterministic
  - step_stochastic(): classical DR via sensor noise
  - step_quantum(): Q-Plugin perturbations
  - step_dr(): full domain-randomized step (action noise, sensor noise, residual)

Domain randomization is applied per-episode via DRRealization (see domain_randomization.py).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from apps.sim.sim.physics.base import PhysicsEngine
from apps.sim.sim.quantum.q_plugin import QPlugin
from apps.sim.sim.sensors.base import SensorModel
from apps.sim.sim.residual.base import ResidualModel


class SimCore:
    """
    Enhanced simulation core with Q-Plugin quantum-stochastic layer
    and domain-randomization support.
    """

    def __init__(
        self,
        physics: PhysicsEngine,
        sensors: list[SensorModel],
        *,
        dt: float = 0.01,
        seed: int | None = None,
        q_plugin: QPlugin | None = None,
        use_q_plugin: bool = False,
        residual_model: ResidualModel | None = None,
    ) -> None:
        self._physics = physics
        self._sensors = sensors
        self._dt = dt
        self._rng = np.random.default_rng(seed)
        self._t = 0.0
        self._state: dict[str, Any] = {}
        self._q_plugin = q_plugin or QPlugin(use_quantum=False, seed=seed)
        self._use_q_plugin = use_q_plugin
        self._residual = residual_model
        self._action_noise_scale: float = 0.0  # set by apply_dr()

    # -- DR configuration (per-episode) ------------------------------------------

    def apply_dr(
        self,
        *,
        noise_scale: float | None = None,
        action_noise_scale: float = 0.0,
    ) -> None:
        """
        Apply domain-randomization overrides for the current episode.
        Physics params (mass, friction, gravity) must be set before building the
        engine; sensor noise can be patched live.
        """
        if noise_scale is not None:
            for sensor in self._sensors:
                if hasattr(sensor, "noise_scale"):
                    sensor.noise_scale = noise_scale  # type: ignore[attr-defined]
                # LatencyWrapper: patch inner sensor
                inner = getattr(sensor, "_sensor", None)
                if inner is not None and hasattr(inner, "noise_scale"):
                    inner.noise_scale = noise_scale  # type: ignore[attr-defined]
        self._action_noise_scale = action_noise_scale

    # -- Reset -------------------------------------------------------------------

    def reset(self, state: dict[str, Any] | None = None, seed: int | None = None) -> None:
        """Reset sim to initial state; optionally reseed RNG."""
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self._t = 0.0
        self._state = self._physics.get_state() if state is None else state
        self._physics.set_state(self._state)

    def step(self, action: dict[str, Any]) -> dict[str, Any]:
        """Deterministic step: no stochasticity."""
        self._physics.apply_action(action, self._dt)
        self._physics.step(self._dt)
        self._state = self._physics.get_state()
        self._t += self._dt
        obs = self._observe(deterministic=True)
        return {
            "t": self._t,
            "state": dict(self._state),
            "observation": obs,
            "action": action,
        }

    def step_stochastic(self, action: dict[str, Any]) -> dict[str, Any]:
        """Stochastic step: classical DR via sensors."""
        self._physics.apply_action(action, self._dt)
        self._physics.step(self._dt)
        self._state = self._physics.get_state()
        self._t += self._dt
        obs = self._observe(deterministic=False)
        return {
            "t": self._t,
            "state": dict(self._state),
            "observation": obs,
            "action": action,
        }

    def step_quantum(self, action: dict[str, Any]) -> dict[str, Any]:
        """
        Quantum-stochastic step: Q-Plugin intercepts and perturbs state.
        next_state = engine_next_state + q_perturbation(s_t, a_t, diagnostics)
        """
        # Get engine diagnostics before step
        diagnostics = getattr(self._physics, "get_diagnostics", lambda: {})()
        # Apply action and step physics
        self._physics.apply_action(action, self._dt)
        self._physics.step(self._dt)
        engine_state = self._physics.get_state()
        # Q-Plugin perturbation
        if self._use_q_plugin:
            self._state = self._q_plugin.perturb_state(
                engine_state, action, diagnostics, seed=self._rng.integers(0, 2**31)
            )
            # Sync perturbed state back to physics (for next step)
            self._physics.set_state(self._state)
        else:
            self._state = engine_state
        self._t += self._dt
        obs = self._observe(deterministic=False)
        return {
            "t": self._t,
            "state": dict(self._state),
            "observation": obs,
            "action": action,
            "q_plugin_used": self._use_q_plugin,
        }

    def step_dr(self, action: dict[str, Any]) -> dict[str, Any]:
        """
        Domain-randomized step: action noise + physics + optional residual correction
        + stochastic observations.  Preferred mode for training with DR.
        """
        # 1. Add action noise
        noisy_action = dict(action)
        if self._action_noise_scale > 0:
            for k, v in noisy_action.items():
                if isinstance(v, list):
                    noisy_action[k] = [
                        x + float(self._rng.normal(0, self._action_noise_scale))
                        for x in v
                    ]
                elif isinstance(v, (int, float)):
                    noisy_action[k] = v + float(self._rng.normal(0, self._action_noise_scale))

        # 2. Physics step
        self._physics.apply_action(noisy_action, self._dt)
        self._physics.step(self._dt)
        engine_state = self._physics.get_state()

        # 3. Q-Plugin perturbation (optional)
        if self._use_q_plugin:
            diagnostics = getattr(self._physics, "get_diagnostics", lambda: {})()
            engine_state = self._q_plugin.perturb_state(
                engine_state, noisy_action, diagnostics,
                seed=self._rng.integers(0, 2**31),
            )

        # 4. Residual correction (optional)
        residual_delta: dict[str, Any] = {}
        if self._residual is not None:
            obs_for_residual = self._observe_from(engine_state, deterministic=True)
            residual_delta = self._residual.predict_delta(engine_state, noisy_action, obs_for_residual)
            for k, dv in residual_delta.items():
                sv = engine_state.get(k)
                if isinstance(sv, list) and isinstance(dv, list):
                    engine_state[k] = [a + b for a, b in zip(sv, dv)]
                elif isinstance(sv, (int, float)) and isinstance(dv, (int, float)):
                    engine_state[k] = sv + dv

        self._state = engine_state
        self._physics.set_state(self._state)
        self._t += self._dt

        obs = self._observe(deterministic=False)
        return {
            "t": self._t,
            "state": dict(self._state),
            "observation": obs,
            "action": action,
            "action_noisy": noisy_action,
            "residual_delta": residual_delta,
            "q_plugin_used": self._use_q_plugin,
        }

    # -- Observation helpers -----------------------------------------------------

    def _observe(self, *, deterministic: bool) -> dict[str, Any]:
        """Build observation from all sensors."""
        return self._observe_from(self._state, deterministic=deterministic)

    def _observe_from(self, state: dict[str, Any], *, deterministic: bool) -> dict[str, Any]:
        """Build observation from a given state (not necessarily self._state)."""
        out: dict[str, Any] = {}
        for sensor in self._sensors:
            name = getattr(sensor, "name", sensor.__class__.__name__)
            out[name] = sensor.observe(
                state, self._t, rng=self._rng if not deterministic else None
            )
        return out

    @property
    def t(self) -> float:
        return self._t

    @property
    def state(self) -> dict[str, Any]:
        return dict(self._state)

    @property
    def dt(self) -> float:
        return self._dt
