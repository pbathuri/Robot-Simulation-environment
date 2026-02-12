"""
CLI entrypoint: run a single scenario and write to runs/<run_id>/.
Usage (from repo root):
  PYTHONPATH=. python -m apps.sim.main
  PYTHONPATH=. python -m apps.sim.main --scenario default --steps 20 --seed 123
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure repo root on path when run as python -m apps.sim.main
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from apps.sim.runner.runner import run_scenario

logging.basicConfig(level=logging.INFO)


def main() -> None:
    p = argparse.ArgumentParser(description="LABLAB Sim – run one scenario")
    p.add_argument("--scenario", default="default", help="Scenario name")
    p.add_argument("--steps", type=int, default=50, help="Number of steps")
    p.add_argument("--seed", type=int, default=42, help="RNG seed")
    p.add_argument("--stochastic", action="store_true", help="Use stochastic stepping")
    p.add_argument("--runs-dir", default="runs", help="Directory for run outputs")
    args = p.parse_args()
    config = {"steps": args.steps, "seed": args.seed, "stochastic": args.stochastic}
    meta = run_scenario(scenario=args.scenario, config=config, runs_dir=args.runs_dir)
    print("Run completed:", meta["run_id"], "→", meta["run_dir"])


if __name__ == "__main__":
    main()
