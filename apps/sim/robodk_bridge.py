"""
RoboDK Bridge: Connect LABLAB to RoboDK for robot programs, CAD sync,
and quantum noise demonstration.

Requires RoboDK installed locally and the `robodk` pip package.
Falls back gracefully when RoboDK is not available.
"""
from __future__ import annotations
import logging
import math
import time
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    from robodk.robolink import (
        Robolink, ITEM_TYPE_ROBOT, ITEM_TYPE_FRAME, ITEM_TYPE_TOOL,
        ITEM_TYPE_OBJECT, ITEM_TYPE_TARGET, ITEM_TYPE_PROGRAM,
    )
    from robodk.robomath import transl, rotx, roty, rotz, Mat, Pose_2_TxyzRxyz, TxyzRxyz_2_Pose
    ROBODK_AVAILABLE = True
except ImportError:
    ROBODK_AVAILABLE = False


class RoboDKBridge:
    """Bridge between LABLAB and RoboDK."""

    def __init__(self) -> None:
        self._rdk = None
        self._connected = False
        if ROBODK_AVAILABLE:
            try:
                self._rdk = Robolink()
                # Quick connectivity test
                self._rdk.ItemList(ITEM_TYPE_FRAME)
                self._connected = True
                logger.info("Connected to RoboDK")
            except Exception as e:
                logger.info("RoboDK not running: %s", e)

    def reconnect(self) -> bool:
        """Attempt to reconnect to RoboDK."""
        if not ROBODK_AVAILABLE:
            return False
        try:
            self._rdk = Robolink()
            self._rdk.ItemList(ITEM_TYPE_FRAME)
            self._connected = True
            return True
        except Exception:
            self._connected = False
            return False

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def available(self) -> bool:
        return ROBODK_AVAILABLE

    # ── Query ─────────────────────────────────────────────────────────────

    def get_station_info(self) -> dict[str, Any]:
        if not self._connected:
            return {"connected": False, "available": ROBODK_AVAILABLE}
        try:
            robots = self._rdk.ItemList(ITEM_TYPE_ROBOT)
            objects = self._rdk.ItemList(ITEM_TYPE_OBJECT)
            frames = self._rdk.ItemList(ITEM_TYPE_FRAME)
            return {
                "connected": True, "available": True,
                "station_name": "RoboDK Station",
                "robots": len(robots),
                "objects": len(objects),
                "frames": len(frames),
                "robot_names": [r.Name() for r in robots],
            }
        except Exception as e:
            self._connected = False
            return {"connected": False, "available": True, "error": str(e)}

    def list_robots(self) -> list[dict[str, Any]]:
        if not self._connected:
            return []
        try:
            robots = self._rdk.ItemList(ITEM_TYPE_ROBOT)
            result = []
            for r in robots:
                joints = r.Joints().tolist()
                pose = Pose_2_TxyzRxyz(r.Pose())
                result.append({
                    "name": r.Name(),
                    "num_joints": len(joints),
                    "joints": joints,
                    "pose_xyzrxyz": pose,
                })
            return result
        except Exception:
            return []

    def list_items(self) -> list[dict[str, Any]]:
        if not self._connected:
            return []
        items = []
        try:
            for item_type, label in [
                (ITEM_TYPE_ROBOT, "robot"), (ITEM_TYPE_FRAME, "frame"),
                (ITEM_TYPE_TOOL, "tool"), (ITEM_TYPE_OBJECT, "object"),
                (ITEM_TYPE_TARGET, "target"),
            ]:
                for item in self._rdk.ItemList(item_type):
                    items.append({"name": item.Name(), "type": label})
        except Exception:
            pass
        return items

    def get_robot_joints(self, robot_name: str) -> list[float]:
        if not self._connected:
            return []
        try:
            robot = self._rdk.Item(robot_name, ITEM_TYPE_ROBOT)
            return robot.Joints().tolist() if robot.Valid() else []
        except Exception:
            return []

    # ── Control ───────────────────────────────────────────────────────────

    def set_robot_joints(self, robot_name: str, joints: list[float]) -> bool:
        if not self._connected:
            return False
        try:
            robot = self._rdk.Item(robot_name, ITEM_TYPE_ROBOT)
            if robot.Valid():
                robot.setJoints(joints)
                return True
        except Exception as e:
            logger.error("set_robot_joints failed: %s", e)
        return False

    def move_to_joints(self, robot_name: str, joints: list[float], blocking: bool = True) -> bool:
        """Move robot to target joints (animated in RoboDK)."""
        if not self._connected:
            return False
        try:
            robot = self._rdk.Item(robot_name, ITEM_TYPE_ROBOT)
            if robot.Valid():
                robot.MoveJ(joints)
                if blocking:
                    robot.WaitMove()
                return True
        except Exception as e:
            logger.error("move_to_joints failed: %s", e)
        return False

    def move_to_target(self, robot_name: str, target_name: str, move_type: str = "joint") -> bool:
        if not self._connected:
            return False
        try:
            robot = self._rdk.Item(robot_name, ITEM_TYPE_ROBOT)
            target = self._rdk.Item(target_name)
            if robot.Valid() and target.Valid():
                if move_type == "linear":
                    robot.MoveL(target)
                else:
                    robot.MoveJ(target)
                return True
        except Exception:
            pass
        return False

    # ── Scene management ──────────────────────────────────────────────────

    def load_robot_from_library(self, robot_filter: str = "") -> dict[str, Any]:
        """Open RoboDK's robot library dialog (or load by filter string)."""
        if not self._connected:
            return {"success": False, "error": "Not connected"}
        try:
            if robot_filter:
                # Try to load from online library by name
                item = self._rdk.AddFile(robot_filter)
                if item and item.Valid():
                    return {"success": True, "name": item.Name(), "num_joints": len(item.Joints().tolist())}
            # Fallback: show selection dialog
            self._rdk.ShowRoboDK()
            return {"success": True, "message": "RoboDK library dialog opened. Select a robot."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_object(self, name: str, file_path: str) -> bool:
        if not self._connected:
            return False
        try:
            item = self._rdk.AddFile(file_path)
            if item and item.Valid():
                item.setName(name)
                return True
        except Exception as e:
            logger.error("Failed to add object: %s", e)
        return False

    def add_frame(self, name: str, position: list[float] | None = None) -> bool:
        """Add a reference frame to the station."""
        if not self._connected:
            return False
        try:
            frame = self._rdk.AddFrame(name)
            if position and len(position) >= 3:
                frame.setPose(transl(position[0] * 1000, position[1] * 1000, position[2] * 1000))
            return True
        except Exception as e:
            logger.error("add_frame failed: %s", e)
        return False

    def add_target(self, name: str, robot_name: str, joints: list[float] | None = None) -> bool:
        """Add a joint target for a robot."""
        if not self._connected:
            return False
        try:
            robot = self._rdk.Item(robot_name, ITEM_TYPE_ROBOT)
            if not robot.Valid():
                return False
            target = self._rdk.AddTarget(name, robot.Parent(), robot)
            if joints:
                target.setJoints(joints)
            else:
                target.setJoints(robot.Joints())
            return True
        except Exception as e:
            logger.error("add_target failed: %s", e)
        return False

    # ── Trajectory playback (LABLAB sim -> RoboDK) ────────────────────────

    def play_trajectory(
        self,
        robot_name: str,
        joint_trajectory: list[list[float]],
        dt: float = 0.05,
    ) -> dict[str, Any]:
        """
        Play a LABLAB simulation trajectory in RoboDK.
        Each entry in joint_trajectory is a list of joint values.
        """
        if not self._connected:
            return {"success": False, "error": "Not connected"}
        try:
            robot = self._rdk.Item(robot_name, ITEM_TYPE_ROBOT)
            if not robot.Valid():
                return {"success": False, "error": f"Robot '{robot_name}' not found"}

            n_steps = len(joint_trajectory)
            for i, joints in enumerate(joint_trajectory):
                robot.setJoints(joints)
                if dt > 0:
                    time.sleep(dt)

            return {"success": True, "steps_played": n_steps}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_quantum_demo(
        self,
        robot_name: str,
        *,
        steps: int = 100,
        noise_scale: float = 0.05,
        seed: int = 42,
    ) -> dict[str, Any]:
        """
        Run a quantum noise demo: move robot through a trajectory,
        then replay with quantum perturbations to show the difference.
        """
        if not self._connected:
            return {"success": False, "error": "Not connected"}

        try:
            robot = self._rdk.Item(robot_name, ITEM_TYPE_ROBOT)
            if not robot.Valid():
                return {"success": False, "error": f"Robot '{robot_name}' not found"}

            n_joints = len(robot.Joints().tolist())
            home = robot.Joints().tolist()
            rng = np.random.default_rng(seed)

            # Generate nominal trajectory (sinusoidal)
            nominal: list[list[float]] = []
            for i in range(steps):
                t = i / steps
                joints = []
                for j in range(n_joints):
                    freq = 0.3 + j * 0.15
                    amp = 20.0 - j * 3.0  # degrees
                    joints.append(home[j] + amp * math.sin(2 * math.pi * freq * t + j * 0.5))
                nominal.append(joints)

            # Generate quantum-perturbed trajectory
            from apps.sim.sim.quantum.q_plugin import QPlugin
            q = QPlugin(use_quantum=False, noise_scale=noise_scale, seed=seed, distribution="mixture")
            perturbed: list[list[float]] = []
            for joints in nominal:
                params = {"state_value": np.mean(joints), "sigma": noise_scale * 10, "velocity": 0.0}
                noise = q.sample(params, n_joints)
                perturbed.append([j + n for j, n in zip(joints, noise)])

            # Play nominal (fast)
            for joints in nominal[::2]:
                robot.setJoints(joints)
                time.sleep(0.02)

            # Brief pause
            time.sleep(0.5)

            # Play perturbed (shows quantum noise effect)
            for joints in perturbed[::2]:
                robot.setJoints(joints)
                time.sleep(0.02)

            # Return to home
            robot.setJoints(home)

            return {
                "success": True,
                "robot": robot_name,
                "steps": steps,
                "noise_scale": noise_scale,
                "nominal_steps": len(nominal),
                "perturbed_steps": len(perturbed),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton (reset on reconnect)
_bridge: RoboDKBridge | None = None


def get_bridge(force_reconnect: bool = False) -> RoboDKBridge:
    global _bridge
    if _bridge is None or force_reconnect:
        _bridge = RoboDKBridge()
    return _bridge
