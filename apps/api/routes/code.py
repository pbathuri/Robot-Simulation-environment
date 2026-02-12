"""Code sandbox API: execute Python snippets with sim imports available."""
from __future__ import annotations
import io
import sys
import traceback
from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/code", tags=["code"])

EXAMPLE_SCRIPTS = {
    "cartpole_demo": {
        "name": "Cartpole Demo",
        "description": "Run cartpole with different noise types and compare rewards.",
        "code": '''from apps.sim.envs.registry import run_episode

# Run with no noise (deterministic)
det = run_episode("cartpole", steps=200, seed=42, noise_scale=0.0)
print(f"Deterministic: {det['total_reward']:.1f} reward, {det['steps_run']} steps")

# Run with classical Gaussian noise
gauss = run_episode("cartpole", steps=200, seed=42, noise_scale=0.05, noise_type="gaussian")
print(f"Gaussian noise: {gauss['total_reward']:.1f} reward, {gauss['steps_run']} steps")

# Run with quantum mixture noise
quantum = run_episode("cartpole", steps=200, seed=42, noise_scale=0.05, noise_type="quantum")
print(f"Quantum noise:  {quantum['total_reward']:.1f} reward, {quantum['steps_run']} steps")

print(f"\\nQuantum noise produces {'more' if quantum['steps_run'] < gauss['steps_run'] else 'fewer'} early terminations")
''',
    },
    "reach_comparison": {
        "name": "Reach Target Comparison",
        "description": "Compare arm reaching performance across noise modes.",
        "code": '''from apps.sim.envs.registry import run_episode

for noise in ["gaussian", "laplace", "mixture", "quantum"]:
    ep = run_episode("reach", steps=200, seed=42, noise_scale=0.03, noise_type=noise)
    final_dist = ep["trajectory"][-1]["render"]["distance"]
    print(f"{noise:10s}: reward={ep['total_reward']:7.2f}, final_dist={final_dist:.4f}")
''',
    },
    "batch_profiles": {
        "name": "Batch Profile Evaluation",
        "description": "Run simulation across multiple reality profiles.",
        "code": '''from apps.sim.runner.batch_runner import run_batch
import tempfile, json

with tempfile.TemporaryDirectory() as tmpdir:
    report = run_batch(
        "examples/simple_robot.urdf",
        profiles=["default", "slippery_warehouse", "noisy_outdoor"],
        steps=30, seed=42, dr_episodes_per_profile=2, runs_dir=tmpdir,
    )
    for pp in report["per_profile"]:
        s = pp["summary"]
        print(f"{pp['profile_id']:20s}: {s['completed']}/{s['total_episodes']} ok, "
              f"step={s['avg_step_time_ms']:.3f}ms")
    print(f"\\nTotal batch time: {report['total_time_s']:.2f}s")
''',
    },
    "quantum_sampling": {
        "name": "Quantum Distribution Sampling",
        "description": "Sample from different noise distributions and compare statistics.",
        "code": '''from apps.sim.sim.quantum.q_plugin import QPlugin
import numpy as np

for dist in ["gaussian", "laplace", "cauchy", "mixture", "bimodal"]:
    plugin = QPlugin(use_quantum=False, noise_scale=0.05, seed=42, distribution=dist)
    samples = plugin.sample({"state_value": 0.5, "sigma": 0.05}, 10000)
    arr = np.array(samples)
    kurtosis = ((arr - arr.mean())**4).mean() / arr.std()**4 - 3
    print(f"{dist:10s}: mean={arr.mean():+.4f} std={arr.std():.4f} kurt={kurtosis:+.2f} "
          f"range=[{arr.min():.3f}, {arr.max():.3f}]")
''',
    },
}


class RunCodeRequest(BaseModel):
    code: str
    timeout: int = 10


@router.get("/examples")
def list_examples() -> dict[str, Any]:
    return {"examples": [
        {"id": k, "name": v["name"], "description": v["description"], "code": v["code"]}
        for k, v in EXAMPLE_SCRIPTS.items()
    ]}


@router.post("/run")
def run_code(req: RunCodeRequest) -> dict[str, Any]:
    """Execute Python code in a sandboxed context with sim imports available."""
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    old_stdout, old_stderr = sys.stdout, sys.stderr

    result: dict[str, Any] = {"success": False, "stdout": "", "stderr": "", "error": None}
    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        exec_globals: dict[str, Any] = {"__builtins__": __builtins__}
        exec(req.code, exec_globals)
        result["success"] = True
    except Exception:
        result["error"] = traceback.format_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        result["stdout"] = stdout_capture.getvalue()
        result["stderr"] = stderr_capture.getvalue()

    return result
