"""Factory/registry for perturbation strategies.

New strategies become available by registering them here (or via
:func:`register`), keeping the orchestrator and CLI decoupled from concrete
strategy classes.
"""

from __future__ import annotations

from typing import Callable, Dict

from .base import PerturbationStrategy
from .boundary import SpecialValueStrategy, ThresholdStraddleStrategy
from .composite import CompositeStrategy

# A factory takes the magnitude knob and returns a ready strategy instance.
StrategyFactory = Callable[[float], PerturbationStrategy]

_REGISTRY: Dict[str, StrategyFactory] = {}


def register(name: str, factory: StrategyFactory) -> None:
    _REGISTRY[name] = factory


def available() -> list[str]:
    return sorted(_REGISTRY)


def create(name: str, magnitude: float = 1.0) -> PerturbationStrategy:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown strategy '{name}'. Available: {', '.join(available())}")
    return _REGISTRY[name](magnitude)


# -- built-in strategies ------------------------------------------------------
# Boundary-aware mutation: choose inputs based on the code's comparison
# constants and on structural edge cases, to deliberately exercise branches.
register("threshold_straddle", lambda m: ThresholdStraddleStrategy(magnitude=m))
register("special_value", lambda m: SpecialValueStrategy(magnitude=m))
# Straddle thresholds where the code has them, else inject special values.
register(
    "boundary",
    lambda m: CompositeStrategy(
        [
            ThresholdStraddleStrategy(magnitude=m),
            SpecialValueStrategy(magnitude=m),
        ],
        name="boundary",
    ),
)
