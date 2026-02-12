"""Optional quantum/quantum-inspired module: Sampler and Optimizer interfaces with classical fallback."""

from apps.sim.quantum.interfaces import Optimizer, Sampler
from apps.sim.quantum.classical_fallback import ClassicalSampler, ClassicalOptimizer

__all__ = ["Sampler", "Optimizer", "ClassicalSampler", "ClassicalOptimizer"]
