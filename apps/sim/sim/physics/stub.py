"""
Rich stub physics engine for demos (no external deps).

Simulates a simple 4-joint planar robot arm with:
  - Forward kinematics (link positions from joint angles)
  - Gravity torques on joints
  - Damping (friction)
  - Joint limits
  - Base position (x, y on ground plane)
  - Contact detection (ground plane)

This produces enough state for the 3D viewport to animate and for
metrics to be meaningful, even without PyBullet.
"""

from __future__ import annotations

import math
from typing import Any

from apps.sim.sim.physics.base import PhysicsEngine


# Robot parameters
NUM_JOINTS = 4
LINK_LENGTHS = [0.15, 0.12, 0.10, 0.08]  # meters
JOINT_LIMITS = [(-2.5, 2.5)] * NUM_JOINTS  # radians
JOINT_DAMPING = 0.3
GRAVITY = -9.81
LINK_MASS = 0.1  # kg per link


class StubPhysicsEngine(PhysicsEngine):
    """
    Multi-joint planar arm on a mobile base.
    State: base_position[3], base_orientation[4], joint_positions[N], joint_velocities[N],
           link_positions[N][3], end_effector[3].
    """

    def __init__(self) -> None:
        self._joint_positions = [0.0] * NUM_JOINTS
        self._joint_velocities = [0.0] * NUM_JOINTS
        self._base_position = [0.0, 0.0, 0.0]
        self._base_velocity = [0.0, 0.0, 0.0]
        self._contacts: list[dict[str, Any]] = []

    def step(self, dt: float) -> None:
        """Advance physics: gravity torques, damping, integration."""
        for j in range(NUM_JOINTS):
            # Gravity torque: proportional to sin(angle) * arm length * mass
            arm_length = sum(LINK_LENGTHS[j:])
            gravity_torque = GRAVITY * LINK_MASS * arm_length * math.sin(self._joint_positions[j]) * 0.1

            # Damping
            damping_torque = -JOINT_DAMPING * self._joint_velocities[j]

            # Integrate velocity
            self._joint_velocities[j] += (gravity_torque + damping_torque) * dt

            # Integrate position
            self._joint_positions[j] += self._joint_velocities[j] * dt

            # Joint limits (bounce)
            lo, hi = JOINT_LIMITS[j]
            if self._joint_positions[j] < lo:
                self._joint_positions[j] = lo
                self._joint_velocities[j] = abs(self._joint_velocities[j]) * 0.3
            elif self._joint_positions[j] > hi:
                self._joint_positions[j] = hi
                self._joint_velocities[j] = -abs(self._joint_velocities[j]) * 0.3

        # Base moves slowly (mobile platform)
        for i in range(3):
            self._base_position[i] += self._base_velocity[i] * dt
            self._base_velocity[i] *= 0.98  # friction

        # Ground contact
        self._contacts = []
        link_positions = self._compute_link_positions()
        for i, lp in enumerate(link_positions):
            if lp[2] <= 0.01:
                self._contacts.append({"link_index": i, "position": list(lp), "normal_force": 0.5})

    def get_state(self) -> dict[str, Any]:
        link_positions = self._compute_link_positions()
        ee = link_positions[-1] if link_positions else [0.0, 0.0, 0.0]
        return {
            "base_position": list(self._base_position),
            "base_orientation": [0.0, 0.0, 0.0, 1.0],
            "joint_positions": list(self._joint_positions),
            "joint_velocities": list(self._joint_velocities),
            "link_positions": [list(lp) for lp in link_positions],
            "end_effector": list(ee),
            "x": self._base_position[0],
            "v": self._base_velocity[0],
        }

    def set_state(self, state: dict[str, Any]) -> None:
        if "joint_positions" in state:
            self._joint_positions = list(state["joint_positions"])[:NUM_JOINTS]
            while len(self._joint_positions) < NUM_JOINTS:
                self._joint_positions.append(0.0)
        if "joint_velocities" in state:
            self._joint_velocities = list(state["joint_velocities"])[:NUM_JOINTS]
            while len(self._joint_velocities) < NUM_JOINTS:
                self._joint_velocities.append(0.0)
        if "base_position" in state:
            self._base_position = list(state["base_position"])[:3]
        if "base_velocity" in state:
            self._base_velocity = list(state["base_velocity"])[:3]
        # Legacy compat
        if "x" in state and "base_position" not in state:
            self._base_position[0] = float(state["x"])
        if "v" in state and "base_velocity" not in state:
            self._base_velocity[0] = float(state["v"])

    def apply_action(self, action: dict[str, Any], dt: float) -> None:
        """
        Apply control action.
        Supports:
          joint_targets: list[float] — PD position control
          joint_torques: list[float] — direct torques
          base_velocity: list[float] — base movement
          v: float — legacy 1D velocity
        """
        if "joint_targets" in action:
            targets = action["joint_targets"]
            kp = 8.0
            kd = 1.5
            for j in range(min(len(targets), NUM_JOINTS)):
                error = targets[j] - self._joint_positions[j]
                self._joint_velocities[j] += (kp * error - kd * self._joint_velocities[j]) * dt

        if "joint_torques" in action:
            torques = action["joint_torques"]
            for j in range(min(len(torques), NUM_JOINTS)):
                self._joint_velocities[j] += torques[j] * dt

        if "base_velocity" in action:
            bv = action["base_velocity"]
            for i in range(min(len(bv), 3)):
                self._base_velocity[i] = bv[i]

        if "v" in action:
            self._base_velocity[0] = float(action["v"])

    def get_diagnostics(self) -> dict[str, Any]:
        return {
            "num_contacts": len(self._contacts),
            "contacts": self._contacts,
        }

    def _compute_link_positions(self) -> list[list[float]]:
        """Forward kinematics: compute 3D positions of each link endpoint."""
        positions = []
        x = self._base_position[0]
        y = self._base_position[1]
        z = 0.15  # base height
        cumulative_angle = 0.0

        for j in range(NUM_JOINTS):
            cumulative_angle += self._joint_positions[j]
            length = LINK_LENGTHS[j]
            # Planar arm in XZ plane
            x += length * math.cos(cumulative_angle)
            z += length * math.sin(cumulative_angle)
            positions.append([x, y, max(z, 0.0)])

        return positions
