"""
In-memory design store: objects manipulable in our environment.
Objects can come from RoboDK (import) or be created locally; pose updates
can be synced back to RoboDK when connected.

Contract:
- list_objects() -> list of object dicts
- get_object(id) -> object dict or None
- put_object(id, payload) -> store/update
- update_pose(id, pose_4x4) -> update pose and optionally sync to RoboDK
- delete_object(id) -> remove
- clear() -> reset store
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

# In-memory store: id -> object dict
_store: dict[str, dict[str, Any]] = {}


def _generate_id() -> str:
    return f"obj_{uuid.uuid4().hex[:12]}"


def list_objects() -> list[dict[str, Any]]:
    """Return all objects in the design (our environment)."""
    return list(_store.values())


def get_object(obj_id: str) -> Optional[dict[str, Any]]:
    """Get one object by id."""
    return _store.get(obj_id)


def put_object(
    obj_id: Optional[str],
    name: str,
    object_type: str = "object",
    pose: Optional[list[list[float]]] = None,
    source: str = "local",
    robodk_id: Optional[str | int] = None,
    geometry_path: Optional[str] = None,
    geometry_url: Optional[str] = None,
    extra: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Create or update an object. If obj_id is None, create new.
    Returns the stored object dict.
    """
    if pose is None:
        pose = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    if obj_id is None or obj_id not in _store:
        obj_id = obj_id or _generate_id()
    payload = {
        "id": obj_id,
        "name": name,
        "type": object_type,
        "pose": pose,
        "source": source,
        "robodk_id": robodk_id,
        "geometry_path": geometry_path,
        "geometry_url": geometry_url,
        **(extra or {}),
    }
    _store[obj_id] = payload
    return payload


def update_pose(obj_id: str, pose_4x4: list[list[float]], sync_to_robodk: bool = False) -> tuple[bool, str]:
    """
    Update object pose in our store. If sync_to_robodk and object has robodk_id, push to RoboDK.
    """
    if obj_id not in _store:
        return False, "Object not found"
    _store[obj_id]["pose"] = pose_4x4
    if sync_to_robodk and _store[obj_id].get("robodk_id") is not None:
        try:
            try:
                from .robodk_bridge import set_item_pose
            except ImportError:
                from apps.sim.robodk_bridge import set_item_pose
            ok, msg = set_item_pose(_store[obj_id]["robodk_id"], pose_4x4)
            if not ok:
                return True, f"Pose updated locally; RoboDK sync failed: {msg}"
        except Exception as e:
            return True, f"Pose updated locally; RoboDK sync error: {e}"
    return True, "OK"


def delete_object(obj_id: str) -> bool:
    """Remove object from store."""
    if obj_id in _store:
        del _store[obj_id]
        return True
    return False


def clear() -> None:
    """Clear all objects (e.g. new design)."""
    _store.clear()
