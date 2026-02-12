"""
Load reality profiles from YAML/JSON.
Profiles define: physics (gravity, friction, restitution), sensors (latency, noise), gap_knobs.
"""

from pathlib import Path
from typing import Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

import json

# Default search path: examples/reality_profiles relative to repo root
def _profiles_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "examples" / "reality_profiles"


def get_profile_path(profile_id: str) -> Path | None:
    """Return path to profile file if it exists."""
    base = _profiles_dir()
    if not base.is_dir():
        return None
    for ext in (".yaml", ".yml", ".json"):
        p = base / f"{profile_id}{ext}"
        if p.is_file():
            return p
    return None


def load_profile(profile_id: str) -> dict[str, Any] | None:
    """
    Load a reality profile by id. Returns dict with physics, sensors, gap_knobs.
    Returns None if not found.
    """
    path = get_profile_path(profile_id)
    if path is None:
        return None
    raw = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        if HAS_YAML:
            return yaml.safe_load(raw)
        return None
    return json.loads(raw)


def list_profiles() -> list[dict[str, Any]]:
    """List all available profiles (id, name, description)."""
    base = _profiles_dir()
    result: list[dict[str, Any]] = []
    if not base.is_dir():
        return result
    for f in base.iterdir():
        if f.suffix not in (".yaml", ".yml", ".json") or not f.is_file():
            continue
        profile_id = f.stem
        data = load_profile(profile_id)
        if data:
            result.append({
                "id": data.get("id", profile_id),
                "name": data.get("name", profile_id),
                "description": data.get("description", ""),
            })
    return result
