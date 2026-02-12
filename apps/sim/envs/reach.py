"""
Reach: 4-joint planar arm must reach a random target position.

State: [joint_angles(4), joint_velocities(4), target_x, target_z, ee_x, ee_z]
Action: [joint_torques(4)] in [-1, 1]
Reward: -distance(end_effector, target) + bonus on close approach
Done: when close enough or max steps
"""
from __future__ import annotations
import math
from typing import Any
import numpy as np
from apps.sim.envs.base import BaseEnv

LINK_LENGTHS = [0.15, 0.12, 0.10, 0.08]
N_JOINTS = 4


class ReachEnv(BaseEnv):
    metadata = {
        "id": "reach",
        "name": "Reach Target",
        "description": "Move a 4-joint arm end-effector to a random target position.",
        "category": "manipulation",
        "obs_keys": ["j0", "j1", "j2", "j3", "jv0", "jv1", "jv2", "jv3", "tgt_x", "tgt_z", "ee_x", "ee_z"],
        "act_keys": ["t0", "t1", "t2", "t3"],
    }

    def __init__(self, *, seed: int | None = None, dt: float = 0.02,
                 noise_scale: float = 0.0, noise_type: str = "gaussian") -> None:
        super().__init__(seed=seed, dt=dt)
        self.max_steps = 200
        self.noise_scale = noise_scale
        self.noise_type = noise_type
        self.joint_pos = np.zeros(N_JOINTS)
        self.joint_vel = np.zeros(N_JOINTS)
        self.target = np.array([0.3, 0.3])
        self.damping = 0.3
        self.success_threshold = 0.03

    @property
    def obs_dim(self) -> int: return 12
    @property
    def act_dim(self) -> int: return 4

    def reset(self, seed: int | None = None) -> np.ndarray:
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.joint_pos = self.rng.uniform(-0.3, 0.3, N_JOINTS)
        self.joint_vel = np.zeros(N_JOINTS)
        r = self.rng.uniform(0.15, 0.4)
        angle = self.rng.uniform(-math.pi / 3, math.pi / 3)
        self.target = np.array([r * math.cos(angle), r * math.sin(angle) + 0.15])
        self.step_count = 0
        return self._obs()

    def step(self, action: np.ndarray | list[float]) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        a = np.clip(np.asarray(action, dtype=np.float64).flatten()[:N_JOINTS], -1, 1) * 2.0
        # Apply torques
        for j in range(N_JOINTS):
            self.joint_vel[j] += (a[j] - self.damping * self.joint_vel[j]) * self.dt
            if self.noise_scale > 0:
                self.joint_vel[j] += float(self.rng.normal(0, self.noise_scale)) * self.dt
            self.joint_pos[j] += self.joint_vel[j] * self.dt
            self.joint_pos[j] = np.clip(self.joint_pos[j], -2.5, 2.5)

        ee = self._fk()
        dist = np.linalg.norm(ee - self.target)
        self.step_count += 1
        reward = -float(dist)
        if dist < self.success_threshold:
            reward += 10.0
        terminated = bool(dist < self.success_threshold)
        truncated = bool(self.step_count >= self.max_steps)
        return self._obs(), reward, terminated, truncated, {"dist": float(dist), "step": self.step_count}

    def _fk(self) -> np.ndarray:
        x, z = 0.0, 0.15
        cum = 0.0
        for j in range(N_JOINTS):
            cum += self.joint_pos[j]
            x += LINK_LENGTHS[j] * math.cos(cum)
            z += LINK_LENGTHS[j] * math.sin(cum)
        return np.array([x, max(z, 0.0)])

    def _link_positions(self) -> list[list[float]]:
        positions = []
        x, z = 0.0, 0.15
        cum = 0.0
        for j in range(N_JOINTS):
            cum += self.joint_pos[j]
            x += LINK_LENGTHS[j] * math.cos(cum)
            z += LINK_LENGTHS[j] * math.sin(cum)
            positions.append([x, 0.0, max(z, 0.0)])
        return positions

    def _obs(self) -> np.ndarray:
        ee = self._fk()
        return np.concatenate([self.joint_pos, self.joint_vel, self.target, ee])

    def render_state(self) -> dict[str, Any]:
        ee = self._fk()
        return {
            "type": "reach",
            "joint_positions": self.joint_pos.tolist(),
            "link_positions": self._link_positions(),
            "end_effector": [float(ee[0]), 0.0, float(ee[1])],
            "target": [float(self.target[0]), 0.0, float(self.target[1])],
            "distance": float(np.linalg.norm(ee - self.target)),
            "step": self.step_count,
        }
