"""3D environment import routes: upload PCD/PLY/OBJ/STL, parse, store."""
from __future__ import annotations
import json
import uuid
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException, UploadFile, File
import numpy as np

router = APIRouter(prefix="/api/environments", tags=["environments-3d"])

_ENVS_DIR = Path(__file__).resolve().parents[3] / "assets" / "environments"


@router.post("/upload")
async def upload_environment(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a 3D environment file (PCD, PLY, OBJ, STL). Returns parsed metadata."""
    _ENVS_DIR.mkdir(parents=True, exist_ok=True)
    name = file.filename or "unknown"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ("pcd", "ply", "obj", "stl"):
        raise HTTPException(400, f"Unsupported format: .{ext}. Use PCD, PLY, OBJ, or STL.")

    env_id = f"env_{uuid.uuid4().hex[:10]}"
    env_dir = _ENVS_DIR / env_id
    env_dir.mkdir(parents=True, exist_ok=True)
    raw_path = env_dir / name
    content = await file.read()
    with open(raw_path, "wb") as f:
        f.write(content)

    # Parse metadata
    meta: dict[str, Any] = {"id": env_id, "filename": name, "format": ext, "size_bytes": len(content)}

    if ext in ("pcd", "ply"):
        points = _parse_point_cloud(raw_path, ext)
        meta["num_points"] = len(points)
        # Downsample for browser
        if len(points) > 100000:
            indices = np.random.default_rng(42).choice(len(points), 100000, replace=False)
            points = points[indices]
        # Save as compact JSON for frontend
        np.save(str(env_dir / "points.npy"), points.astype(np.float32))
        meta["bounds"] = {
            "min": points.min(axis=0).tolist(),
            "max": points.max(axis=0).tolist(),
        }
        # Also save as JSON list for easy frontend fetch
        pts_json = env_dir / "points.json"
        with open(pts_json, "w") as f:
            json.dump(points.tolist(), f)
    elif ext in ("obj", "stl"):
        meta["type"] = "mesh"

    with open(env_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    return meta


@router.get("/list")
def list_environments_3d() -> dict[str, Any]:
    if not _ENVS_DIR.is_dir():
        return {"environments": []}
    envs = []
    for d in _ENVS_DIR.iterdir():
        if not d.is_dir():
            continue
        meta_path = d / "meta.json"
        if meta_path.is_file():
            with open(meta_path) as f:
                envs.append(json.load(f))
    return {"environments": envs}


@router.get("/{env_id}/points")
def get_environment_points(env_id: str, limit: int = 50000) -> dict[str, Any]:
    """Return point cloud data for 3D rendering."""
    env_dir = _ENVS_DIR / env_id
    pts_path = env_dir / "points.json"
    if not pts_path.is_file():
        raise HTTPException(404, "Points not found for this environment")
    with open(pts_path) as f:
        points = json.load(f)
    return {"env_id": env_id, "num_points": len(points), "points": points[:limit]}


@router.get("/{env_id}/meta")
def get_environment_meta(env_id: str) -> dict[str, Any]:
    meta_path = _ENVS_DIR / env_id / "meta.json"
    if not meta_path.is_file():
        raise HTTPException(404, "Environment not found")
    with open(meta_path) as f:
        return json.load(f)


def _parse_point_cloud(path: Path, fmt: str) -> np.ndarray:
    """Parse PCD or PLY to Nx3 numpy array."""
    if fmt == "ply":
        return _parse_ply(path)
    elif fmt == "pcd":
        return _parse_pcd(path)
    return np.zeros((0, 3))


def _parse_ply(path: Path) -> np.ndarray:
    """Simple ASCII PLY parser. Handles header then x y z per line."""
    points = []
    in_data = False
    n_vertices = 0
    with open(path, "r", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("element vertex"):
                n_vertices = int(line.split()[-1])
            elif line == "end_header":
                in_data = True
                continue
            elif in_data:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        points.append([float(parts[0]), float(parts[1]), float(parts[2])])
                    except ValueError:
                        continue
                if len(points) >= n_vertices and n_vertices > 0:
                    break
    return np.array(points) if points else np.zeros((0, 3))


def _parse_pcd(path: Path) -> np.ndarray:
    """Simple ASCII PCD parser."""
    points = []
    in_data = False
    with open(path, "r", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line == "DATA ascii":
                in_data = True
                continue
            elif in_data:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        points.append([float(parts[0]), float(parts[1]), float(parts[2])])
                    except ValueError:
                        continue
    return np.array(points) if points else np.zeros((0, 3))
