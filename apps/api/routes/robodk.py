"""
RoboDK + Design API: connect, import from RoboDK, and fully manipulate objects
in our environment (design store) with optional sync to RoboDK.
"""
from __future__ import annotations

import os
import tempfile
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Bridge and store - support same-repo or installed package
try:
    from apps.sim.robodk_bridge import (
        add_object_to_robodk,
        connect as rdk_connect,
        export_item_geometry,
        get_station_tree,
        import_item as rdk_import_item,
        run_quantum_demo,
        set_item_pose,
        set_robot_joints,
    )
    from apps.sim.design_store import (
        delete_object as store_delete,
        get_object as store_get,
        list_objects as store_list,
        put_object as store_put,
        update_pose as store_update_pose,
    )
except ImportError:
    import sys
    # routes/ -> api/ -> apps/ -> repo root
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    try:
        from apps.sim.robodk_bridge import (
            add_object_to_robodk,
            connect as rdk_connect,
            export_item_geometry,
            get_station_tree,
            import_item as rdk_import_item,
            run_quantum_demo,
            set_item_pose,
            set_robot_joints,
        )
        from apps.sim.design_store import (
            delete_object as store_delete,
            get_object as store_get,
            list_objects as store_list,
            put_object as store_put,
            update_pose as store_update_pose,
        )
    except ImportError:
        from sim.robodk_bridge import (
            add_object_to_robodk,
            connect as rdk_connect,
            export_item_geometry,
            get_station_tree,
            import_item as rdk_import_item,
            run_quantum_demo,
            set_item_pose,
            set_robot_joints,
        )
        from sim.design_store import (
            delete_object as store_delete,
            get_object as store_get,
            list_objects as store_list,
            put_object as store_put,
            update_pose as store_update_pose,
        )

router = APIRouter(prefix="/api/robodk", tags=["robodk"])


# --- Request/Response models ---

class PoseUpdate(BaseModel):
    pose: list[list[float]]  # 4x4 row-major
    sync_to_robodk: bool = False


class SetJointsRequest(BaseModel):
    robot_name: str
    joints: list[float]


class AddObjectRequest(BaseModel):
    name: str
    pose: Optional[list[list[float]]] = None


class CreateObjectRequest(BaseModel):
    name: str
    object_type: str = "object"
    pose: Optional[list[list[float]]] = None


# --- RoboDK connection & import ---

@router.get("/status")
def robodk_status():
    """Check if RoboDK is connected."""
    ok, msg = rdk_connect()
    return {"connected": ok, "message": msg}


@router.post("/connect")
def robodk_connect_endpoint():
    """Explicitly connect to RoboDK."""
    ok, msg = rdk_connect()
    if not ok:
        raise HTTPException(status_code=503, detail=msg)
    return {"connected": True, "message": msg}


@router.get("/station")
def get_station():
    """Import full station tree from RoboDK."""
    ok, msg, roots = get_station_tree()
    if not ok:
        raise HTTPException(status_code=503, detail=msg)
    return {"items": roots, "message": msg}


@router.get("/import/{item_ref}")
def import_from_robodk(item_ref: str):
    """
    Import one item from RoboDK by name or id into our environment.
    Item is added to the design store and returned (geometry_path may be a temp file).
    """
    try:
        item_id_int = int(item_ref)
    except ValueError:
        item_id_int = item_ref
    ok, msg, payload = rdk_import_item(item_id_int)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    # Normalize geometry_path to URL or base64 later; for now omit or pass path for backend serve
    # Store in our design store so it's manipulable
    stored = store_put(
        obj_id=None,
        name=payload["name"],
        object_type=payload.get("type_name", "object"),
        pose=payload["pose"],
        source="robodk",
        robodk_id=payload.get("id") or payload.get("name"),
        geometry_path=payload.get("geometry_path"),
        extra={"raw_robodk": {k: v for k, v in payload.items() if k not in ("geometry_path",)}},
    )
    return {"imported": payload, "stored_id": stored["id"], "object": stored}


@router.post("/import-all")
def import_all_from_station():
    """Import all items from the current RoboDK station tree into our design store."""
    ok, msg, roots = get_station_tree()
    if not ok:
        raise HTTPException(status_code=503, detail=msg)

    def flatten(items: list, acc: list):
        for it in items:
            acc.append(it)
            flatten(it.get("children") or [], acc)

    flat = []
    flatten(roots, flat)
    imported = []
    for it in flat:
        name = it.get("name") or str(it.get("id", ""))
        robodk_id = it.get("id") or name
        stored = store_put(
            obj_id=None,
            name=name,
            object_type=it.get("type_name", "object"),
            pose=it.get("pose"),
            source="robodk",
            robodk_id=robodk_id,
            extra={"raw_robodk": it},
        )
        imported.append({"name": name, "stored_id": stored["id"]})
    return {"imported": imported, "count": len(imported)}


# --- Design store (our environment): full CRUD ---

@router.get("/design/objects")
def list_design_objects():
    """List all objects in our design environment (from RoboDK or created locally)."""
    return {"objects": store_list()}


@router.get("/design/objects/{obj_id}")
def get_design_object(obj_id: str):
    """Get one object by id."""
    obj = store_get(obj_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    return obj


@router.put("/design/objects/{obj_id}/pose")
def update_design_object_pose(obj_id: str, body: PoseUpdate):
    """Update object pose in our environment; optionally sync to RoboDK."""
    ok, msg = store_update_pose(obj_id, body.pose, sync_to_robodk=body.sync_to_robodk)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    obj = store_get(obj_id)
    return {"updated": True, "object": obj, "sync_message": msg}


@router.delete("/design/objects/{obj_id}")
def delete_design_object(obj_id: str):
    """Remove object from our design (does not delete in RoboDK)."""
    if not store_delete(obj_id):
        raise HTTPException(status_code=404, detail="Object not found")
    return {"deleted": True, "id": obj_id}


@router.post("/design/objects")
def create_design_object(body: CreateObjectRequest):
    """Create a new object in our environment (no RoboDK)."""
    obj = store_put(
        obj_id=None,
        name=body.name,
        object_type=body.object_type,
        pose=body.pose,
        source="local",
    )
    return obj


# --- Push to RoboDK / control ---

@router.post("/design/objects/{obj_id}/sync-to-robodk")
def sync_object_to_robodk(obj_id: str):
    """Push current pose of this object to RoboDK (if it has robodk_id)."""
    obj = store_get(obj_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    rid = obj.get("robodk_id")
    if rid is None:
        raise HTTPException(status_code=400, detail="Object has no RoboDK link; import from RoboDK first")
    ok, msg = set_item_pose(rid, obj["pose"])
    if not ok:
        raise HTTPException(status_code=502, detail=msg)
    return {"synced": True, "message": msg}


@router.post("/robots/joints")
def set_robot_joints_endpoint(body: SetJointsRequest):
    """Set robot joint angles in RoboDK."""
    ok, msg = set_robot_joints(body.robot_name, body.joints)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.post("/quantum-demo")
def quantum_demo_endpoint(robot_name: str = "Robot", duration_sec: float = 5.0):
    """Run quantum demo in RoboDK (nominal vs perturbed motion)."""
    ok, msg = run_quantum_demo(robot_name, duration_sec)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


# --- Add file to RoboDK and optionally to our design store ---

@router.post("/add-file")
async def add_file_to_robodk(file: UploadFile, name: Optional[str] = None, add_to_design: bool = True):
    """
    Upload a geometry file (STL, STEP, etc.); add to RoboDK station and optionally to our design store.
    """
    suffix = os.path.splitext(file.filename or "")[1] or ".stl"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        path = tmp.name
    try:
        obj_name = name or (file.filename or "imported").replace(" ", "_")
        ok, msg, item_dict = add_object_to_robodk(path, obj_name, pose_4x4=None)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        if add_to_design and item_dict:
            stored = store_put(
                obj_id=None,
                name=item_dict.get("name", obj_name),
                object_type=item_dict.get("type_name", "object"),
                pose=item_dict.get("pose"),
                source="robodk",
                robodk_id=item_dict.get("id") or item_dict.get("name"),
                extra={"added_from_file": file.filename},
            )
            return {"robodk": item_dict, "design_object": stored}
        return {"robodk": item_dict}
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


# --- Export geometry ---

@router.get("/export/{item_ref}", response_class=FileResponse)
def export_geometry(item_ref: str):
    """Export item geometry from RoboDK; returns STL file for download."""
    try:
        item_id = int(item_ref)
    except ValueError:
        item_id = item_ref
    fd, path = tempfile.mkstemp(suffix=".stl")
    os.close(fd)
    ok, msg = export_item_geometry(item_id, path)
    if not ok:
        try:
            os.unlink(path)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=msg)
    return FileResponse(path, filename=f"export_{item_ref}.stl", media_type="application/octet-stream")
