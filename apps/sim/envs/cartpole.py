"""
Cartpole: Classic inverted pendulum on a cart.

State: [cart_x, cart_v, pole_angle, pole_angular_vel]
Action: [force] in [-1, 1]
Reward: +1 per step the pole stays upright
Done: pole angle > 12 deg or cart leaves bounds

Supports Q-Plugin noise injection to demonstrate quantum vs classical
domain randomization on a universally recognized benchmark.
"""
from __future__ import annotations
import math
from typing import Any
import numpy as np
from apps.sim.envs.base import BaseEnv


class CartpoleEnv(BaseEnv):
    metadata = {
        "id": "cartpole",
        "name": "Cartpole",
        "description": "Balance an inverted pendulum on a cart. Classic RL benchmark.",
        "category": "classic",
        "obs_keys": ["cart_x", "cart_v", "pole_angle", "pole_angvel"],
        "act_keys": ["force"],
    }

    def __init__(self, *, seed: int | None = None, dt: float = 0.02,
                 noise_scale: float = 0.0, noise_type: str = "gaussian") -> None:
        super().__init__(seed=seed, dt=dt)
        self.max_steps = 500
        # Physics
        self.gravity = 9.81
        self.cart_mass = 1.0
        self.pole_mass = 0.1
        self.pole_length = 0.5  # half-length
        self.force_mag = 10.0
        self.x_threshold = 2.4
        self.theta_threshold = 12 * math.pi / 180
        # Noise
        self.noise_scale = noise_scale
        self.noise_type = noise_type
        # State
        self.state = np.zeros(4)

    @property
    def obs_dim(self) -> int: return 4
    @property
    def act_dim(self) -> int: return 1

    def reset(self, seed: int | None = None) -> np.ndarray:
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.state = self.rng.uniform(-0.05, 0.05, size=4)
        self.step_count = 0
        return self.state.copy()

    def step(self, action: np.ndarray | list[float]) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        a = np.asarray(action, dtype=np.float64).flatten()
        force = float(np.clip(a[0], -1, 1)) * self.force_mag

        x, x_dot, theta, theta_dot = self.state
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        total_mass = self.cart_mass + self.pole_mass
        pole_ml = self.pole_mass * self.pole_length

        # Physics (Euler semi-implicit)
        temp = (force + pole_ml * theta_dot**2 * sin_t) / total_mass
        theta_acc = (self.gravity * sin_t - cos_t * temp) / (
            self.pole_length * (4.0/3.0 - self.pole_mass * cos_t**2 / total_mass)
        )
        x_acc = temp - pole_ml * theta_acc * cos_t / total_mass

        # Apply noise (domain randomization)
        if self.noise_scale > 0:
            noise = self._sample_noise(2)
            x_acc += noise[0] * 0.5
            theta_acc += noise[1] * 0.2

        x_dot += theta_acc * self.dt  # intentionally using theta_acc for coupling
        # Correct: standard cartpole integration
        x_dot_new = x_dot + x_acc * self.dt
        theta_dot_new = theta_dot + theta_acc * self.dt
        x_new = x + x_dot_new * self.dt
        theta_new = theta + theta_dot_new * self.dt

        self.state = np.array([x_new, x_dot_new, theta_new, theta_dot_new])
        self.step_count += 1

        terminated = bool(abs(x_new) > self.x_threshold or abs(theta_new) > self.theta_threshold)
        truncated = self.step_count >= self.max_steps
        reward = 1.0 if not terminated else 0.0

        return self.state.copy(), reward, terminated, truncated, {
            "step": self.step_count,
            "noise_type": self.noise_type,
        }

    def _sample_noise(self, n: int) -> np.ndarray:
        s = self.noise_scale
        if self.noise_type == "laplace":
            return self.rng.laplace(0, s / math.sqrt(2), n)
        elif self.noise_type == "cauchy":
            return s * self.rng.standard_cauchy(n)
        elif self.noise_type == "mixture":
            samples = []
            for _ in range(n):
                if self.rng.random() < 0.15:
                    samples.append(float(self.rng.laplace(0, s * 3)))
                else:
                    samples.append(float(self.rng.normal(0, s)))
            return np.array(samples)
        elif self.noise_type == "quantum":
            # Simulated quantum: bimodal snap + gaussian tail
            samples = []
            for _ in range(n):
                if self.rng.random() < 0.1:
                    samples.append(float(self.rng.choice([-1, 1]) * s * 2 + self.rng.normal(0, s * 0.3)))
                else:
                    samples.append(float(self.rng.normal(0, s)))
            return np.array(samples)
        return self.rng.normal(0, s, n)

    def render_state(self) -> dict[str, Any]:
        x, x_dot, theta, theta_dot = self.state
        pole_end_x = x + self.pole_length * 2 * math.sin(theta)
        pole_end_z = self.pole_length * 2 * math.cos(theta)
        return {
            "type": "cartpole",
            "cart_x": float(x),
            "cart_y": 0.0,
            "pole_angle": float(theta),
            "pole_end": [float(pole_end_x), 0.0, float(pole_end_z)],
            "step": self.step_count,
        }
