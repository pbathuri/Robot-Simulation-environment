"""RoboDK bridge API routes."""
from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/robodk", tags=["robodk"])

# Temporary storage for uploaded files
UPLOAD_DIR = Path("assets/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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


class CreateObjectRequest(BaseModel):
    name: str
    object_type: str = "object"
    pose: Optional[List[float]] = None
    source: str = "local"
    robodk_id: Optional[str] = None


class UpdatePoseRequest(BaseModel):
    pose: List[float]
    sync_to_robodk: bool = False


class SyncRequest(BaseModel):
    sync_to_robodk: bool = True


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


@router.get("/station")
def get_station() -> dict[str, Any]:
    """Get full station tree."""
    from apps.sim.robodk_bridge import get_bridge
    bridge = get_bridge()
    return {"station_tree": bridge.get_station_tree(), "connected": bridge.connected}


@router.get("/joints/{robot_name}")
def get_joints(robot_name: str) -> dict[str, Any]:
    from apps.sim.robodk_bridge import get_bridge
    bridge = get_bridge()
    joints = bridge.get_robot_joints(robot_name)
    return {"robot_name": robot_name, "joints": joints, "connected": bridge.connected}


# ── Import/Export ────────────────────────────────────────────────────────


@router.get("/import/{item_ref:path}")
def import_item(item_ref: str) -> dict[str, Any]:
    """Import an item (by name or ID) from RoboDK into local design store."""
    from apps.sim.robodk_bridge import get_bridge
    from apps.sim.design_store import create_object

    bridge = get_bridge()
    if not bridge.connected:
        raise HTTPException(503, "RoboDK not connected")

    result = bridge.import_item(item_ref)
    if not result.get("success"):
        raise HTTPException(
            404, f"Item '{item_ref}' not found or import failed: {result.get('error')}")

    # Add to design store
    obj = create_object(
        name=result["name"],
        object_type=result["type"],
        pose=result["pose"],
        source="robodk",
        robodk_id=item_ref,
        metadata={"robodk_parent": result.get("parent_name")}
    )
    return {"object": obj}


@router.post("/import-all")
def import_all_items() -> dict[str, Any]:
    """Import all items from RoboDK station to local store."""
    from apps.sim.robodk_bridge import get_bridge
    from apps.sim.design_store import create_object, clear_store

    bridge = get_bridge()
    if not bridge.connected:
        raise HTTPException(503, "RoboDK not connected")

    items = bridge.list_items()
    imported_count = 0

    for item in items:
        res = bridge.import_item(item["name"])
        if res.get("success"):
            create_object(
                name=res["name"],
                object_type=res["type"],
                pose=res["pose"],
                source="robodk",
                robodk_id=item["name"],
                metadata={"robodk_parent": res.get("parent_name")}
            )
            imported_count += 1

    return {"imported_count": imported_count, "total_items": len(items)}


@router.post("/add-file")
async def add_file(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a file (STL, STEP, etc.) and add to RoboDK station."""
    from apps.sim.robodk_bridge import get_bridge

    bridge = get_bridge()
    if not bridge.connected:
        raise HTTPException(503, "RoboDK not connected")

    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    success = bridge.add_object_to_robodk(str(file_path), file.filename)
    if not success:
        raise HTTPException(500, "Failed to add object to RoboDK")

    return {"filename": file.filename, "path": str(file_path), "success": True}


@router.get("/export/{item_ref:path}")
def export_item(item_ref: str) -> FileResponse:
    """Export item geometry from RoboDK as STL."""
    from apps.sim.robodk_bridge import get_bridge

    bridge = get_bridge()
    if not bridge.connected:
        raise HTTPException(503, "RoboDK not connected")

    # Sanitize filename (handle slashes in robot names like "ABB .../...")
    safe_name = item_ref.replace("/", "_").replace("\\", "_")
    out_path = UPLOAD_DIR / f"{safe_name}.stl"

    success = bridge.export_item_geometry(item_ref, str(out_path.resolve()))

    if not success or not out_path.exists() or out_path.stat().st_size == 0:
        raise HTTPException(
            500, "Failed to export item (empty or missing file)")

    return FileResponse(out_path, filename=f"{safe_name}.stl")


# ── Design Store API ─────────────────────────────────────────────────────


@router.get("/design/objects")
def list_design_objects() -> dict[str, Any]:
    from apps.sim.design_store import list_objects
    return {"objects": list_objects()}


@router.get("/design/objects/{object_id}")
def get_design_object(object_id: str) -> dict[str, Any]:
    from apps.sim.design_store import get_object
    obj = get_object(object_id)
    if not obj:
        raise HTTPException(404, "Object not found")
    return obj


@router.post("/design/objects")
def create_design_object(req: CreateObjectRequest) -> dict[str, Any]:
    from apps.sim.design_store import create_object
    return create_object(
        name=req.name,
        object_type=req.object_type,
        pose=req.pose,
        source=req.source,
        robodk_id=req.robodk_id
    )


@router.put("/design/objects/{object_id}/pose")
def update_object_pose(object_id: str, req: UpdatePoseRequest) -> dict[str, Any]:
    from apps.sim.design_store import update_object, get_object
    from apps.sim.robodk_bridge import get_bridge

    obj = get_object(object_id)
    if not obj:
        raise HTTPException(404, "Object not found")

    updated = update_object(object_id, {"pose": req.pose})

    # Sync to RoboDK if requested and linked
    if req.sync_to_robodk and obj.get("robodk_id"):
        bridge = get_bridge()
        if bridge.connected:
            bridge.set_item_pose(obj["robodk_id"], req.pose)

    return updated


@router.post("/design/objects/{object_id}/sync-to-robodk")
def sync_to_robodk(object_id: str) -> dict[str, Any]:
    from apps.sim.design_store import get_object
    from apps.sim.robodk_bridge import get_bridge

    obj = get_object(object_id)
    if not obj:
        raise HTTPException(404, "Object not found")
    if not obj.get("robodk_id"):
        raise HTTPException(400, "Object not linked to RoboDK")

    bridge = get_bridge()
    if not bridge.connected:
        raise HTTPException(503, "RoboDK not connected")

    success = bridge.set_item_pose(obj["robodk_id"], obj["pose"])
    return {"success": success}


@router.delete("/design/objects/{object_id}")
def delete_design_object(object_id: str) -> dict[str, Any]:
    from apps.sim.design_store import delete_object
    if delete_object(object_id):
        return {"success": True}
    raise HTTPException(404, "Object not found")


# ── Control ───────────────────────────────────────────────────────────────


def _require_connected():
    from apps.sim.robodk_bridge import get_bridge
    b = get_bridge()
    if not b.connected:
        raise HTTPException(
            503, "RoboDK not connected. Start RoboDK and call POST /api/robodk/reconnect.")
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
