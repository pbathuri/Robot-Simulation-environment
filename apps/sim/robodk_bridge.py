"""
RoboDK bridge: connect to RoboDK, import station/items, get geometry/poses,
and push updates so objects are fully manipulable from our environment via API.

Contract:
- connect(): (bool, message)
- get_station_tree(): list of item dicts (id, name, type, pose, children, geometry_path)
- import_item(item_name_or_id): full item payload for our scene
- set_item_pose(item_name_or_id, pose_4x4_list): apply pose in RoboDK
- set_robot_joints(robot_name, joints_list): set robot joint angles
- add_object_to_robodk(file_path, name, pose): add object from file to station
- export_item_geometry(item_name_or_id, output_path): export mesh to file (STL)
"""
from __future__ import annotations

import logging
import os
import tempfile
from math import sin
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Optional RoboDK dependency
try:
    from robodk.robolink import (
        ITEM_TYPE_FRAME,
        ITEM_TYPE_OBJECT,
        ITEM_TYPE_ROBOT,
        ITEM_TYPE_STATION,
        ITEM_TYPE_TARGET,
        ITEM_TYPE_TOOL,
        Robolink,
    )
    from robodk.robomath import pose_2_xyzrpw, xyzrpw_2_pose
    RDK_AVAILABLE = True
except ImportError:
    RDK_AVAILABLE = False
    ITEM_TYPE_STATION = 1
    Robolink = None  # type: ignore

# Type names for our API
ITEM_TYPE_NAMES = {
    1: "station",
    2: "robot",
    3: "frame",
    4: "tool",
    5: "object",
    6: "target",
    7: "curve",
    8: "program",
    10: "program_python",
    17: "folder",
    18: "robot_arm",
    19: "camera",
    20: "generic",
    21: "robot_axes",
    22: "notes",
}


def _pose_to_list(pose) -> list[list[float]]:
    """Convert RoboDK 4x4 pose matrix to list of 4 lists (row-major)."""
    if pose is None:
        return [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    try:
        return [[float(pose[i, j]) for j in range(4)] for i in range(4)]
    except Exception:
        return [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]


def _list_to_pose(rows: list[list[float]]):
    """Convert list of 4x4 to RoboDK pose matrix (if robomath available)."""
    if not RDK_AVAILABLE or not rows or len(rows) != 4:
        return None
    from robodk.robomath import rotz  # 4x4 identity base
    try:
        from robodk.robomath import identity
        pose = identity(4)
        for i in range(4):
            for j in range(4):
                pose[i, j] = float(rows[i][j])
        return pose
    except Exception:
        return None


def connect() -> tuple[bool, str]:
    """Establish link with RoboDK. Returns (success, message)."""
    if not RDK_AVAILABLE:
        return False, "RoboDK Python API (robodk) not installed. pip install robodk"
    try:
        rdk = Robolink()
        # Trigger a simple call to verify connection
        _ = rdk.Item(0)
        return True, "Connected to RoboDK"
    except Exception as e:
        logger.exception("RoboDK connect failed")
        return False, str(e)


def _get_rdk() -> Optional[Any]:
    if not RDK_AVAILABLE:
        return None
    try:
        return Robolink()
    except Exception:
        return None


def _item_to_dict(item) -> Optional[dict]:
    """Serialize one Item to a dict (name, type, type_name, pose, id)."""
    if item is None or (hasattr(item, "Valid") and not item.Valid()):
        return None
    try:
        raw_type = item.Type()
        pose = item.Pose()
        try:
            link = item.getLink()
            item_id = getattr(link, "id", None) or 0
        except Exception:
            item_id = 0
        return {
            "id": item_id,
            "name": item.Name(),
            "type": raw_type,
            "type_name": ITEM_TYPE_NAMES.get(raw_type, "generic"),
            "pose": _pose_to_list(pose),
            "children": [],
        }
    except Exception as e:
        logger.warning("_item_to_dict failed: %s", e)
        return None


def get_station_tree() -> tuple[bool, str, list]:
    """
    Recursively get full station tree from RoboDK.
    Returns (success, message, list of root-level item dicts with nested children).
    """
    rdk = _get_rdk()
    if rdk is None:
        return False, "RoboDK not available", []

    def recurse(it):
        d = _item_to_dict(it)
        if d is None:
            return None
        try:
            child_list = []
            for i in range(it.ChildCount()):
                c = it.Child(i)
                cd = recurse(c)
                if cd:
                    child_list.append(cd)
            d["children"] = child_list
        except Exception:
            pass
        return d

    try:
        station = rdk.Item("", ITEM_TYPE_STATION)
        roots = []
        try:
            for i in range(station.ChildCount()):
                child = station.Child(i)
                node = recurse(child)
                if node:
                    roots.append(node)
        except Exception as e:
            logger.warning("get_station_tree recurse: %s", e)
        return True, "OK", roots
    except Exception as e:
        logger.exception("get_station_tree failed")
        return False, str(e), []


def get_item_by_name_or_id(name_or_id: str | int):
    """Resolve item by name or numeric id. Returns Item or None."""
    rdk = _get_rdk()
    if rdk is None:
        return None
    try:
        if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
            item = rdk.Item(int(name_or_id))
        else:
            item = rdk.Item(str(name_or_id))
        if item.Valid():
            return item
    except Exception:
        pass
    return None


def import_item(name_or_id: str | int) -> tuple[bool, str, Optional[dict]]:
    """
    Import a single item from RoboDK into our internal representation.
    Returns (success, message, payload).
    Payload: name, type, type_name, pose, id, geometry_path (if exported), children.
    """
    item = get_item_by_name_or_id(name_or_id)
    if item is None:
        return False, "Item not found", None
    d = _item_to_dict(item)
    if d is None:
        return False, "Could not serialize item", None
    # Optionally export geometry to temp file for our viewer
    geometry_path = None
    try:
        if item.Type() == ITEM_TYPE_OBJECT or item.Type() == ITEM_TYPE_TOOL:
            fd, path = tempfile.mkstemp(suffix=".stl")
            os.close(fd)
            item.ExportGeometry(path)
            if os.path.isfile(path):
                geometry_path = path
    except Exception as e:
        logger.debug("Export geometry failed (non-fatal): %s", e)
    d["geometry_path"] = geometry_path
    # Recursive children (without geometry for speed; can be requested per child)
    try:
        d["children"] = []
        for i in range(item.ChildCount()):
            c = item.Child(i)
            cd = _item_to_dict(c)
            if cd:
                d["children"].append(cd)
    except Exception:
        pass
    return True, "OK", d


def set_item_pose(name_or_id: str | int, pose_4x4: list[list[float]]) -> tuple[bool, str]:
    """Set item pose in RoboDK from 4x4 matrix (row-major)."""
    item = get_item_by_name_or_id(name_or_id)
    if item is None:
        return False, "Item not found"
    pose = _list_to_pose(pose_4x4)
    if pose is None:
        return False, "Invalid pose matrix"
    try:
        item.setPose(pose)
        return True, "OK"
    except Exception as e:
        return False, str(e)


def set_robot_joints(robot_name: str, joints: list[float]) -> tuple[bool, str]:
    """Set robot joint angles (degrees or rad depending on RoboDK config)."""
    item = get_item_by_name_or_id(robot_name)
    if item is None:
        return False, "Robot not found"
    try:
        if item.Type() != ITEM_TYPE_ROBOT and item.Type() != 18:
            return False, "Item is not a robot"
        item.setJoints(joints)
        return True, "OK"
    except Exception as e:
        return False, str(e)


def add_object_to_robodk(file_path: str, name: str, pose_4x4: Optional[list[list[float]]] = None) -> tuple[bool, str, Optional[dict]]:
    """
    Add an object from file (STL, STEP, etc.) to the current RoboDK station.
    Returns (success, message, item_dict).
    """
    rdk = _get_rdk()
    if rdk is None:
        return False, "RoboDK not available", None
    if not os.path.isfile(file_path):
        return False, "File not found", None
    try:
        item = rdk.AddFile(file_path)
        if item is None or not item.Valid():
            return False, "AddFile failed", None
        if name:
            item.setName(name)
        if pose_4x4:
            p = _list_to_pose(pose_4x4)
            if p is not None:
                item.setPose(p)
        return True, "OK", _item_to_dict(item)
    except Exception as e:
        return False, str(e), None


def export_item_geometry(name_or_id: str | int, output_path: str) -> tuple[bool, str]:
    """Export item mesh to STL (or other supported format)."""
    item = get_item_by_name_or_id(name_or_id)
    if item is None:
        return False, "Item not found"
    try:
        item.ExportGeometry(output_path)
        return True, "OK"
    except Exception as e:
        return False, str(e)


def run_quantum_demo(robot_name: str, duration_sec: float = 5.0) -> tuple[bool, str]:
    """Run a short demo in RoboDK comparing nominal vs quantum-perturbed motion."""
    import time
    item = get_item_by_name_or_id(robot_name)
    if item is None:
        return False, "Robot not found"
    try:
        joints = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        item.setJoints(joints)
        t0 = time.time()
        while time.time() - t0 < duration_sec:
            t = time.time() - t0
            j = [0.1 * sin(t * 2), 0.1 * sin(t * 2.1), 0.0, 0.0, 0.0, 0.0]
            item.setJoints([a + b for a, b in zip(joints, j)])
            time.sleep(0.05)
        item.setJoints(joints)
        return True, "Demo finished"
    except Exception as e:
        return False, str(e)
