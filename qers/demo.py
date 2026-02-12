"""
QERS MVP demo: loads example robot, runs sim, shows metrics.
Usage: PYTHONPATH=. python -m qers.demo
"""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run QERS demo."""
    repo_root = Path(__file__).resolve().parents[1]
    examples_dir = repo_root / "examples"
    examples_dir.mkdir(exist_ok=True)

    # Create a minimal example URDF if none exists
    example_urdf = examples_dir / "simple_robot.urdf"
    if not example_urdf.is_file():
        urdf_content = """<?xml version="1.0"?>
<robot name="simple_robot">
  <link name="base_link">
    <visual>
      <geometry>
        <box size="0.2 0.2 0.1"/>
      </geometry>
      <material name="blue">
        <color rgba="0 0 1 1"/>
      </material>
    </visual>
    <collision>
      <geometry>
        <box size="0.2 0.2 0.1"/>
      </geometry>
    </collision>
    <inertial>
      <mass value="1.0"/>
      <inertia ixx="0.01" ixy="0" ixz="0" iyy="0.01" iyz="0" izz="0.01"/>
    </inertial>
  </link>
</robot>
"""
        example_urdf.write_text(urdf_content)
        logger.info(f"Created example URDF: {example_urdf}")

    # Run simulation
    from apps.sim.runner.qers_runner import run_qers_sim

    logger.info("Running QERS demo simulation...")
    meta = run_qers_sim(
        urdf_path=str(example_urdf),
        steps=50,
        dt=0.01,
        seed=42,
        use_q_plugin=False,  # Use classical fallback for MVP
        reality_profile="slippery_warehouse",  # Demo profile: low friction, 50ms latency
        runs_dir=str(repo_root / "runs"),
    )
    logger.info(f"Demo completed: run_id={meta['run_id']}")
    logger.info(f"Metrics: {meta['metrics']}")
    logger.info(f"Run directory: {meta['run_dir']}")
    print("\n✅ QERS demo completed successfully!")
    print(f"   Run ID: {meta['run_id']}")
    print(f"   Avg step time: {meta['metrics']['avg_step_time_ms']:.2f} ms")
    print(f"   Total steps: {meta['metrics']['steps']}")


if __name__ == "__main__":
    main()
