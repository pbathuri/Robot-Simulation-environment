"""
In-memory store for design objects (CAD models, robots) in the simulation environment.
Allows manipulating objects locally and syncing them with RoboDK.
"""
import uuid
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# In-memory store: {object_id: object_data}
_objects: Dict[str, Dict[str, Any]] = {}


def list_objects() -> List[Dict[str, Any]]:
    """List all objects in the store."""
    return list(_objects.values())


def get_object(object_id: str) -> Optional[Dict[str, Any]]:
    """Get a single object by ID."""
    return _objects.get(object_id)


def create_object(
    name: str,
    object_type: str = "object",
    pose: Optional[List[float]] = None,
    source: str = "local",
    robodk_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a new object in the store."""
    object_id = str(uuid.uuid4())
    # Default identity pose (4x4 matrix flattened)
    if pose is None:
        pose = [
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0
        ]

    obj = {
        "id": object_id,
        "name": name,
        "type": object_type,
        "pose": pose,
        "source": source,
        "robodk_id": robodk_id,  # Name or Item ID in RoboDK
        "metadata": metadata or {}
    }
    _objects[object_id] = obj
    return obj


def update_object(object_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update object properties."""
    if object_id not in _objects:
        return None

    obj = _objects[object_id]

    # Handle pose updates specifically to ensure format
    if "pose" in updates:
        obj["pose"] = updates["pose"]

    # Update other fields
    for k, v in updates.items():
        if k != "id":  # ID is immutable
            obj[k] = v

    return obj


def delete_object(object_id: str) -> bool:
    """Delete an object from the store."""
    if object_id in _objects:
        del _objects[object_id]
        return True
    return False


def clear_store():
    """Clear all objects."""
    _objects.clear()
