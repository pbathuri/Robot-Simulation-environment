"""
Segment mesh/asset into parts. Stub: single part or simple split.
Full impl would use ML segmentation or trimesh decomposition.
"""

from pathlib import Path
from typing import Any


def segment_asset(asset_path: str | Path) -> dict[str, Any]:
    """
    Input: path to mesh or URDF. Output: { parts: [ { id, name, mesh_path? } ], asset_type }.
    Stub: if URDF, return one part per link; if mesh file, return single part or simple split.
    """
    path = Path(asset_path)
    if not path.is_file():
        return {"parts": [], "asset_type": "unknown", "error": "file not found"}
    suffix = path.suffix.lower()
    if suffix == ".urdf":
        # Stub: parse minimal URDF for link names
        try:
            text = path.read_text()
            parts = []
            if "<link " in text:
                import re
                for m in re.finditer(r'<link\s+name="([^"]+)"', text):
                    parts.append({"id": m.group(1), "name": m.group(1), "mesh_path": None})
            if not parts:
                parts = [{"id": "base_link", "name": "base_link", "mesh_path": None}]
            return {"parts": parts, "asset_type": "urdf"}
        except Exception as e:
            return {"parts": [], "asset_type": "urdf", "error": str(e)}
    if suffix in (".obj", ".stl", ".ply"):
        # Stub: single part or trimesh split if available
        try:
            import trimesh
            mesh = trimesh.load(path)
            if isinstance(mesh, trimesh.Scene):
                parts = [{"id": f"part_{i}", "name": n or f"part_{i}", "mesh_path": str(path)} for i, n in enumerate(mesh.geometry.keys())]
            else:
                parts = [{"id": "part_0", "name": path.stem, "mesh_path": str(path)}]
            return {"parts": parts, "asset_type": "mesh"}
        except ImportError:
            return {"parts": [{"id": "part_0", "name": path.stem, "mesh_path": str(path)}], "asset_type": "mesh"}
    return {"parts": [{"id": "part_0", "name": path.stem, "mesh_path": str(path)}], "asset_type": "unknown"}
