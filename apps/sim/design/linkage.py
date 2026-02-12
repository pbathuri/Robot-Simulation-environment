"""
Linkage: parts + edges/joint types → linkage spec; optional export to URDF.
"""

from pathlib import Path
from typing import Any


def build_linkage_spec(parts: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    """
    parts: [ { id, name, mesh_path? } ]
    edges: [ { parent_id, child_id, joint_type? } ]  joint_type: hinge, fixed, continuous, prismatic
    Returns linkage_spec for export.
    """
    return {
        "parts": parts,
        "edges": edges,
        "joint_types": {f"{e['parent_id']}_{e['child_id']}": e.get("joint_type", "fixed") for e in edges},
    }


def export_linkage_to_urdf(linkage_spec: dict[str, Any], output_path: str | Path) -> str:
    """
    Generate minimal URDF from linkage spec and write to output_path.
    Returns path as string.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = linkage_spec.get("parts", [])
    edges = linkage_spec.get("edges", [])
    joint_types = linkage_spec.get("joint_types", {})
    robot_name = "robot"
    lines = ['<?xml version="1.0"?>', f'<robot name="{robot_name}">']
    for p in parts:
        pid = p.get("id", "part")
        name = p.get("name", pid)
        lines.append(f'  <link name="{name}">')
        lines.append('    <visual><geometry><box size="0.1 0.1 0.1"/></geometry></visual>')
        lines.append('    <collision><geometry><box size="0.1 0.1 0.1"/></geometry></collision>')
        lines.append('    <inertial><mass value="1"/><inertia ixx="0.01" iyy="0.01" izz="0.01" ixy="0" ixz="0" iyz="0"/></inertial>')
        lines.append("  </link>")
    for e in edges:
        parent = e.get("parent_id", "base")
        child = e.get("child_id", "link")
        jtype = joint_types.get(f"{parent}_{child}", "fixed")
        jname = f"joint_{parent}_{child}"
        lines.append(f'  <joint name="{jname}" type="{jtype}">')
        lines.append(f'    <parent link="{parent}"/>')
        lines.append(f'    <child link="{child}"/>')
        lines.append('    <origin xyz="0 0 0" rpy="0 0 0"/>')
        if jtype in ("revolute", "continuous"):
            lines.append('    <axis xyz="0 0 1"/>')
        lines.append("  </joint>")
    lines.append("</robot>")
    path.write_text("\n".join(lines))
    return str(path)
