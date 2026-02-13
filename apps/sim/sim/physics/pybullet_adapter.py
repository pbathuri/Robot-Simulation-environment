"""
PyBullet physics adapter: implements PhysicsEngine interface.
Loads URDF, steps physics, returns state in neutral format.
"""

from __future__ import annotations
from typing import Any

import numpy as np

try:
    import pybullet as p
    PYBULLET_AVAILABLE = True
except ImportError:
    PYBULLET_AVAILABLE = False
    p = None  # type: ignore

from apps.sim.sim.physics.base import PhysicsEngine


class PyBulletAdapter(PhysicsEngine):
    """
    PyBullet adapter: loads URDF, steps physics, exposes state/actions.
    State: {link_positions: [...], link_velocities: [...], joint_positions: [...], ...}
    """

    def __init__(
        self,
        urdf_path: str | None = None,
        *,
        gravity: tuple[float, float, float] = (0, 0, -9.81),
        timestep: float = 0.01,
        use_gui: bool = False,
    ) -> None:
        if not PYBULLET_AVAILABLE:
            raise ImportError(
                "PyBullet not available. Install with: pip install pybullet"
                " or use StubPhysicsEngine for MVP."
            )
        self._urdf_path = urdf_path
        self._gravity = gravity
        self._timestep = timestep
        self._use_gui = use_gui
        self._client_id: int | None = None
        self._robot_id: int | None = None
        self._joint_indices: list[int] = []
        self._link_indices: list[int] = []
        self._initialized = False

    def initialize(self) -> None:
        """Initialize PyBullet client and load robot."""
        if self._initialized:
            return
        mode = p.GUI if self._use_gui else p.DIRECT
        self._client_id = p.connect(mode)
        p.setGravity(*self._gravity)
        p.setTimeStep(self._timestep)
        if self._urdf_path:
            self._robot_id = p.loadURDF(
                self._urdf_path,
                basePosition=[0, 0, 0],
                baseOrientation=[0, 0, 0, 1],
                physicsClientId=self._client_id,
            )
            # Get joint and link info
            num_joints = p.getNumJoints(self._robot_id, physicsClientId=self._client_id)
            self._joint_indices = list(range(num_joints))
            self._link_indices = [-1] + list(range(num_joints))  # base + links
        self._initialized = True

    def step(self, dt: float) -> None:
        """Advance physics by dt."""
        if not self._initialized:
            self.initialize()
        p.stepSimulation(physicsClientId=self._client_id)

    def get_state(self) -> dict[str, Any]:
        """Return current state: positions, velocities, orientations."""
        if not self._initialized:
            self.initialize()
        if self._robot_id is None:
            return {"base_position": [0, 0, 0], "base_orientation": [0, 0, 0, 1]}
        state: dict[str, Any] = {}
        # Base pose
        base_pos, base_orn = p.getBasePositionAndOrientation(
            self._robot_id, physicsClientId=self._client_id
        )
        state["base_position"] = list(base_pos)
        state["base_orientation"] = list(base_orn)
        # Joint states
        joint_states = p.getJointStates(
            self._robot_id, self._joint_indices, physicsClientId=self._client_id
        )
        state["joint_positions"] = [js[0] for js in joint_states]
        state["joint_velocities"] = [js[1] for js in joint_states]
        # Link positions (approximate)
        link_positions = []
        for link_idx in self._link_indices:
            if link_idx == -1:
                link_positions.append(list(base_pos))
            else:
                link_info = p.getLinkState(
                    self._robot_id, link_idx, physicsClientId=self._client_id
                )
                link_positions.append(list(link_info[0]))
        state["link_positions"] = link_positions
        return state

    def set_state(self, state: dict[str, Any]) -> None:
        """Set state for replay/reset."""
        if not self._initialized:
            self.initialize()
        if self._robot_id is None:
            return
        base_pos = state.get("base_position", [0, 0, 0])
        base_orn = state.get("base_orientation", [0, 0, 0, 1])
        p.resetBasePositionAndOrientation(
            self._robot_id, base_pos, base_orn, physicsClientId=self._client_id
        )
        joint_positions = state.get("joint_positions", [])
        joint_velocities = state.get("joint_velocities", [])
        for i, (pos, vel) in enumerate(zip(joint_positions, joint_velocities)):
            p.resetJointState(
                self._robot_id, self._joint_indices[i], pos, vel, physicsClientId=self._client_id
            )

    def apply_action(self, action: dict[str, Any], dt: float) -> None:
        """Apply control action: joint torques or target positions."""
        if not self._initialized:
            self.initialize()
        if self._robot_id is None:
            return
        # Support both torque control and position control
        if "joint_torques" in action:
            torques = action["joint_torques"]
            p.setJointMotorControlArray(
                self._robot_id,
                self._joint_indices,
                p.TORQUE_CONTROL,
                forces=torques,
                physicsClientId=self._client_id,
            )
        elif "joint_targets" in action:
            targets = action["joint_targets"]
            p.setJointMotorControlArray(
                self._robot_id,
                self._joint_indices,
                p.POSITION_CONTROL,
                targetPositions=targets,
                physicsClientId=self._client_id,
            )

    def get_diagnostics(self) -> dict[str, Any]:
        """Return engine diagnostics: contacts, forces, etc."""
        if not self._initialized or self._robot_id is None:
            return {}
        contacts = p.getContactPoints(physicsClientId=self._client_id)
        return {
            "num_contacts": len(contacts),
            "contacts": [
                {
                    "link_a": c[3],
                    "link_b": c[4],
                    "normal": list(c[7]),
                    "force": c[9],
                }
                for c in contacts[:10]  # Limit to first 10
            ],
        }

    def close(self) -> None:
        """Disconnect PyBullet client."""
        if self._client_id is not None:
            p.disconnect(physicsClientId=self._client_id)
            self._client_id = None
            self._initialized = False
