"""
Walker2D: Simple planar biped locomotion.

State: [body_x, body_z, body_vx, body_vz, body_angle, body_angvel,
        hip_L, hip_L_v, knee_L, knee_L_v, hip_R, hip_R_v, knee_R, knee_R_v]
Action: [hip_L_torque, knee_L_torque, hip_R_torque, knee_R_torque] in [-1,1]
Reward: forward velocity - energy cost - fall penalty
"""
from __future__ import annotations
import math
from typing import Any
import numpy as np
from apps.sim.envs.base import BaseEnv

THIGH_LEN = 0.15
SHIN_LEN = 0.15
BODY_HEIGHT = 0.3


class Walker2DEnv(BaseEnv):
    metadata = {
        "id": "walker2d",
        "name": "Walker 2D",
        "description": "A planar biped must walk forward. Locomotion benchmark.",
        "category": "locomotion",
        "obs_keys": ["bx", "bz", "bvx", "bvz", "ba", "bav", "hL", "hLv", "kL", "kLv", "hR", "hRv", "kR", "kRv"],
        "act_keys": ["hipL", "kneeL", "hipR", "kneeR"],
    }

    def __init__(self, *, seed: int | None = None, dt: float = 0.02,
                 noise_scale: float = 0.0, noise_type: str = "gaussian") -> None:
        super().__init__(seed=seed, dt=dt)
        self.max_steps = 500
        self.noise_scale = noise_scale
        self.gravity = 9.81
        self.state_vec = np.zeros(14)

    @property
    def obs_dim(self) -> int: return 14
    @property
    def act_dim(self) -> int: return 4

    def reset(self, seed: int | None = None) -> np.ndarray:
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.state_vec = np.zeros(14)
        self.state_vec[1] = BODY_HEIGHT  # body_z
        self.step_count = 0
        return self.state_vec.copy()

    def step(self, action: np.ndarray | list[float]) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        a = np.clip(np.asarray(action, dtype=np.float64).flatten()[:4], -1, 1) * 3.0
        s = self.state_vec
        bx, bz, bvx, bvz, ba, bav = s[0], s[1], s[2], s[3], s[4], s[5]
        joints = s[6:].reshape(4, 2)  # [angle, velocity] for hipL, kneeL, hipR, kneeR

        # Joint dynamics
        for i in range(4):
            joints[i, 1] += (a[i] - 0.3 * joints[i, 1]) * self.dt
            if self.noise_scale > 0:
                joints[i, 1] += float(self.rng.normal(0, self.noise_scale)) * self.dt
            joints[i, 0] += joints[i, 1] * self.dt
            joints[i, 0] = np.clip(joints[i, 0], -1.5, 1.5)

        # Foot positions (simplified)
        foot_L = self._foot_pos(bx, bz, ba, joints[0, 0], joints[1, 0], side=-1)
        foot_R = self._foot_pos(bx, bz, ba, joints[2, 0], joints[3, 0], side=1)

        # Ground contact forces
        ground_force_z = 0.0
        ground_force_x = 0.0
        for foot in [foot_L, foot_R]:
            if foot[1] <= 0.01:
                penetration = 0.01 - foot[1]
                ground_force_z += 80.0 * penetration
                ground_force_x += 0.3 * (joints[0, 1] + joints[2, 1])

        # Body dynamics
        bvz += (-self.gravity + ground_force_z / 1.0) * self.dt
        bvx += ground_force_x * self.dt * 0.5
        bvx *= 0.99
        bz += bvz * self.dt
        bx += bvx * self.dt
        ba += bav * self.dt
        bav += (-0.5 * ba - 0.1 * bav) * self.dt  # Restoring torque

        bz = max(bz, 0.1)

        self.state_vec = np.array([bx, bz, bvx, bvz, ba, bav,
                                   joints[0, 0], joints[0, 1], joints[1, 0], joints[1, 1],
                                   joints[2, 0], joints[2, 1], joints[3, 0], joints[3, 1]])
        self.step_count += 1

        # Reward
        forward_vel = bvx
        energy = np.sum(a ** 2) * 0.001
        alive_bonus = 1.0
        reward = forward_vel + alive_bonus - energy

        terminated = bool(bz < 0.15 or abs(ba) > 1.0)
        truncated = bool(self.step_count >= self.max_steps)

        return self.state_vec.copy(), float(reward), terminated, truncated, {
            "forward_vel": float(forward_vel),
            "step": self.step_count,
        }

    def _foot_pos(self, bx: float, bz: float, ba: float, hip: float, knee: float, side: int) -> np.ndarray:
        hip_x = bx + side * 0.05 * math.cos(ba + math.pi / 2)
        hip_z = bz - 0.05
        thigh_angle = ba + hip
        knee_angle = thigh_angle + knee
        knee_x = hip_x + THIGH_LEN * math.sin(thigh_angle)
        knee_z = hip_z - THIGH_LEN * math.cos(thigh_angle)
        foot_x = knee_x + SHIN_LEN * math.sin(knee_angle)
        foot_z = knee_z - SHIN_LEN * math.cos(knee_angle)
        return np.array([foot_x, foot_z])

    def render_state(self) -> dict[str, Any]:
        s = self.state_vec
        joints = s[6:].reshape(4, 2)
        foot_L = self._foot_pos(s[0], s[1], s[4], joints[0, 0], joints[1, 0], -1)
        foot_R = self._foot_pos(s[0], s[1], s[4], joints[2, 0], joints[3, 0], 1)
        return {
            "type": "walker2d",
            "body_pos": [float(s[0]), 0.0, float(s[1])],
            "body_angle": float(s[4]),
            "joints": {"hipL": float(joints[0, 0]), "kneeL": float(joints[1, 0]),
                        "hipR": float(joints[2, 0]), "kneeR": float(joints[3, 0])},
            "foot_L": [float(foot_L[0]), 0.0, float(foot_L[1])],
            "foot_R": [float(foot_R[0]), 0.0, float(foot_R[1])],
            "step": self.step_count,
        }
