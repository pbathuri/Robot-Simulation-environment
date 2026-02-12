"""
Push: Robot arm pushes a box to a goal position.

State: [joint_angles(4), joint_velocities(4), box_x, box_z, goal_x, goal_z, ee_x, ee_z]
Action: [joint_torques(4)] in [-1, 1]
Reward: -distance(box, goal) + shaping
Contact-rich: showcases Q-Plugin contact-aware noise scaling.
"""
from __future__ import annotations
import math
from typing import Any
import numpy as np
from apps.sim.envs.base import BaseEnv

LINK_LENGTHS = [0.15, 0.12, 0.10, 0.08]
N_JOINTS = 4
BOX_SIZE = 0.04


class PushEnv(BaseEnv):
    metadata = {
        "id": "push",
        "name": "Push Object",
        "description": "Push a box to a goal position with a 4-joint arm. Contact-rich benchmark.",
        "category": "manipulation",
        "obs_keys": ["j0-3", "jv0-3", "box_x", "box_z", "goal_x", "goal_z", "ee_x", "ee_z"],
        "act_keys": ["t0", "t1", "t2", "t3"],
    }

    def __init__(self, *, seed: int | None = None, dt: float = 0.02,
                 noise_scale: float = 0.0, noise_type: str = "gaussian") -> None:
        super().__init__(seed=seed, dt=dt)
        self.max_steps = 300
        self.noise_scale = noise_scale
        self.joint_pos = np.zeros(N_JOINTS)
        self.joint_vel = np.zeros(N_JOINTS)
        self.box_pos = np.array([0.25, 0.05])
        self.box_vel = np.array([0.0, 0.0])
        self.goal = np.array([0.35, 0.05])

    @property
    def obs_dim(self) -> int: return 14
    @property
    def act_dim(self) -> int: return 4

    def reset(self, seed: int | None = None) -> np.ndarray:
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.joint_pos = self.rng.uniform(-0.2, 0.2, N_JOINTS)
        self.joint_vel = np.zeros(N_JOINTS)
        self.box_pos = np.array([self.rng.uniform(0.15, 0.3), 0.05])
        self.box_vel = np.zeros(2)
        angle = self.rng.uniform(0, 2 * math.pi)
        self.goal = self.box_pos + np.array([math.cos(angle), math.sin(angle)]) * self.rng.uniform(0.08, 0.15)
        self.goal[1] = max(self.goal[1], 0.02)
        self.step_count = 0
        return self._obs()

    def step(self, action: np.ndarray | list[float]) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        a = np.clip(np.asarray(action, dtype=np.float64).flatten()[:N_JOINTS], -1, 1) * 2.0

        for j in range(N_JOINTS):
            self.joint_vel[j] += (a[j] - 0.3 * self.joint_vel[j]) * self.dt
            if self.noise_scale > 0:
                self.joint_vel[j] += float(self.rng.normal(0, self.noise_scale)) * self.dt
            self.joint_pos[j] += self.joint_vel[j] * self.dt
            self.joint_pos[j] = np.clip(self.joint_pos[j], -2.5, 2.5)

        ee = self._fk()
        # Contact: if EE is close to box, push it
        ee2d = np.array([ee[0], ee[1]])
        contact_dist = np.linalg.norm(ee2d - self.box_pos)
        n_contacts = 0
        if contact_dist < BOX_SIZE + 0.02:
            push_dir = (self.box_pos - ee2d)
            push_dir_norm = np.linalg.norm(push_dir)
            if push_dir_norm > 1e-6:
                push_dir /= push_dir_norm
            force = max(0, BOX_SIZE + 0.02 - contact_dist) * 5.0
            self.box_vel += push_dir * force * self.dt
            n_contacts = 1

        self.box_vel *= 0.95  # friction
        self.box_pos += self.box_vel * self.dt
        self.box_pos[1] = max(self.box_pos[1], 0.01)

        self.step_count += 1
        box_goal_dist = float(np.linalg.norm(self.box_pos - self.goal))
        ee_box_dist = float(contact_dist)
        reward = -box_goal_dist - 0.1 * ee_box_dist
        if box_goal_dist < 0.02:
            reward += 10.0
        terminated = bool(box_goal_dist < 0.02)
        truncated = bool(self.step_count >= self.max_steps)

        return self._obs(), reward, terminated, truncated, {
            "box_goal_dist": box_goal_dist,
            "contacts": n_contacts,
            "step": self.step_count,
        }

    def _fk(self) -> np.ndarray:
        x, z = 0.0, 0.15
        cum = 0.0
        for j in range(N_JOINTS):
            cum += self.joint_pos[j]
            x += LINK_LENGTHS[j] * math.cos(cum)
            z += LINK_LENGTHS[j] * math.sin(cum)
        return np.array([x, max(z, 0.0)])

    def _obs(self) -> np.ndarray:
        ee = self._fk()
        return np.concatenate([self.joint_pos, self.joint_vel, self.box_pos, self.goal, ee])

    def render_state(self) -> dict[str, Any]:
        ee = self._fk()
        return {
            "type": "push",
            "joint_positions": self.joint_pos.tolist(),
            "end_effector": [float(ee[0]), 0.0, float(ee[1])],
            "box_pos": [float(self.box_pos[0]), 0.0, float(self.box_pos[1])],
            "box_size": BOX_SIZE,
            "goal_pos": [float(self.goal[0]), 0.0, float(self.goal[1])],
            "step": self.step_count,
        }
