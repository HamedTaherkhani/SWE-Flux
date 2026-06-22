"""Composite strategy: apply several strategies in order to each literal."""

from __future__ import annotations

from typing import List, Optional

from .base import Number, PerturbationContext, PerturbationStrategy


class CompositeStrategy(PerturbationStrategy):
    """Chain strategies; the first that returns a value wins for each literal.

    This lets us, e.g., complicate both floats and ints in one pass while keeping
    each child strategy small and single-purpose.
    """

    name = "composite"

    def __init__(self, children: List[PerturbationStrategy], name: Optional[str] = None) -> None:
        if not children:
            raise ValueError("CompositeStrategy requires at least one child strategy")
        self.children = children
        if name:
            self.name = name

    def perturb_constant(self, value: Number, ctx: PerturbationContext) -> Optional[Number]:
        for child in self.children:
            new = child.perturb_constant(value, ctx)
            if new is not None and new != value:
                return new
        return None

    def perturb_sequence(
        self, values: List[Number], ctx: PerturbationContext
    ) -> Optional[List[Number]]:
        for child in self.children:
            new = child.perturb_sequence(values, ctx)
            if new is not None and list(new) != list(values):
                return new
        return None

    def describe(self) -> str:
        return f"{self.name}({'+'.join(c.name for c in self.children)})"
