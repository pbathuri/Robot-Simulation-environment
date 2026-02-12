"""RoboDK bridge API routes."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/robodk", tags=["robodk"])


class JointsRequest(BaseModel):
    robot_name: str
    joints: list[float]


class MoveRequest(BaseModel):
    robot_name: str
    target_name: str
    move_type: str = "joint"


class AddObjectRequest(BaseModel):
    name: str
    file_path: str


class AddFrameRequest(BaseModel):
    name: str
    position: list[float] | None = None


class AddTargetRequest(BaseModel):
    name: str
    robot_name: str
    joints: list[float] | None = None


class LoadRobotRequest(BaseModel):
    robot_filter: str = ""


class TrajectoryRequest(BaseModel):
    robot_name: str
    joint_trajectory: list[list[float]]
    dt: float = 0.05


class QuantumDemoRequest(BaseModel):
    robot_name: str
    steps: int = 100
    noise_scale: float = 0.05
    seed: int = 42


# ── Queries ───────────────────────────────────────────────────────────────


@router.get("/status")
def robodk_status() -> dict[str, Any]:
    from apps.sim.robodk_bridge import get_bridge
    return get_bridge().get_station_info()


@router.post("/reconnect")
def reconnect() -> dict[str, Any]:
    from apps.sim.robodk_bridge import get_bridge
    bridge = get_bridge(force_reconnect=True)
    return bridge.get_station_info()


@router.get("/robots")
def list_robots() -> dict[str, Any]:
    from apps.sim.robodk_bridge import get_bridge
    bridge = get_bridge()
    return {"robots": bridge.list_robots(), "connected": bridge.connected}


@router.get("/items")
def list_items() -> dict[str, Any]:
    from apps.sim.robodk_bridge import get_bridge
    bridge = get_bridge()
    return {"items": bridge.list_items(), "connected": bridge.connected}


@router.get("/joints/{robot_name}")
def get_joints(robot_name: str) -> dict[str, Any]:
    from apps.sim.robodk_bridge import get_bridge
    bridge = get_bridge()
    joints = bridge.get_robot_joints(robot_name)
    return {"robot_name": robot_name, "joints": joints, "connected": bridge.connected}


# ── Control ───────────────────────────────────────────────────────────────


def _require_connected():
    from apps.sim.robodk_bridge import get_bridge
    b = get_bridge()
    if not b.connected:
        raise HTTPException(503, "RoboDK not connected. Start RoboDK and call POST /api/robodk/reconnect.")
    return b


@router.post("/set-joints")
def set_joints(req: JointsRequest) -> dict[str, Any]:
    b = _require_connected()
    return {"success": b.set_robot_joints(req.robot_name, req.joints)}


@router.post("/move")
def move_robot(req: MoveRequest) -> dict[str, Any]:
    b = _require_connected()
    return {"success": b.move_to_target(req.robot_name, req.target_name, req.move_type)}


@router.post("/move-joints")
def move_to_joints(req: JointsRequest) -> dict[str, Any]:
    b = _require_connected()
    return {"success": b.move_to_joints(req.robot_name, req.joints)}


# ── Scene ─────────────────────────────────────────────────────────────────


@router.post("/load-robot")
def load_robot(req: LoadRobotRequest) -> dict[str, Any]:
    """Load a robot from RoboDK library or open library dialog."""
    b = _require_connected()
    return b.load_robot_from_library(req.robot_filter)


@router.post("/add-object")
def add_object(req: AddObjectRequest) -> dict[str, Any]:
    b = _require_connected()
    return {"success": b.add_object(req.name, req.file_path)}


@router.post("/add-frame")
def add_frame(req: AddFrameRequest) -> dict[str, Any]:
    b = _require_connected()
    return {"success": b.add_frame(req.name, req.position)}


@router.post("/add-target")
def add_target(req: AddTargetRequest) -> dict[str, Any]:
    b = _require_connected()
    return {"success": b.add_target(req.name, req.robot_name, req.joints)}


# ── Trajectory & Quantum Demo ────────────────────────────────────────────


@router.post("/play-trajectory")
def play_trajectory(req: TrajectoryRequest) -> dict[str, Any]:
    """Play a LABLAB simulation trajectory on a robot in RoboDK."""
    b = _require_connected()
    return b.play_trajectory(req.robot_name, req.joint_trajectory, req.dt)


@router.post("/quantum-demo")
def quantum_demo(req: QuantumDemoRequest) -> dict[str, Any]:
    """
    Run quantum noise demo on a robot in RoboDK:
    1. Play nominal trajectory (smooth)
    2. Replay with quantum perturbations (shows noise effect visually)
    """
    b = _require_connected()
    return b.run_quantum_demo(
        req.robot_name, steps=req.steps,
        noise_scale=req.noise_scale, seed=req.seed,
    )
