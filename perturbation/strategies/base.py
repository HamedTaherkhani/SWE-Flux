"""Strategy pattern for input perturbation.

A strategy is a pure value transformer: given a numeric literal (and a little
context) it returns a *new, harder* value or ``None`` to leave it unchanged.
Structural protection (shapes, dims, dtypes) is handled by the AST driver, so
strategies only worry about how to complicate a data value.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

Number = Union[int, float]


@dataclass
class PerturbationContext:
    """Context handed to a strategy for a single literal."""

    rng: random.Random
    keyword_name: Optional[str] = None  # kwarg name if literal is a kwarg value
    enclosing_call: Optional[str] = None  # name of the nearest enclosing call
    magnitude: float = 1.0
    # Candidate branch thresholds (numeric constants the code compares against),
    # used by boundary-aware strategies to deliberately straddle branches.
    thresholds: Tuple[float, ...] = ()
    # When True, sequence perturbations must keep the vector length unchanged
    # (so shape-coupled code keeps working).
    preserve_length: bool = True


class PerturbationStrategy(ABC):
    """Base class for all perturbation strategies.

    Two optional hooks let a strategy act at different granularities:

    * :meth:`perturb_constant` -- transform a single scalar literal.
    * :meth:`perturb_sequence` -- transform a flat numeric vector (e.g. grow a
      1-D ``np.array([...])``). Multi-dimensional / shape literals are never
      passed here, so structure stays consistent.

    A strategy may implement either or both; the default implementations are
    no-ops, so value strategies ignore sequences and sequence strategies ignore
    scalars.
    """

    #: Stable identifier used in CLI/config and in generated instance ids.
    name: str = "base"

    def perturb_constant(self, value: Number, ctx: PerturbationContext) -> Optional[Number]:
        """Return a replacement value, or ``None`` to leave ``value`` unchanged."""
        return None

    def perturb_sequence(
        self, values: List[Number], ctx: PerturbationContext
    ) -> Optional[List[Number]]:
        """Return a new list of values (e.g. longer), or ``None`` for no change."""
        return None

    def describe(self) -> str:
        return self.name
