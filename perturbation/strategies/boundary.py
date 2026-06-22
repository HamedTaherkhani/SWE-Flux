"""Boundary-aware perturbation strategies.

These use the candidate branch thresholds in :class:`PerturbationContext`
(numeric constants the code/test compares against) to *deliberately* exercise
branch boundaries, instead of relying on random values to happen to cross them.

* :class:`ThresholdStraddleStrategy` -- replaces a numeric vector with values
  that sit just-below / at / just-above each threshold (plus zero and a clear
  negative/large), and snaps scalars onto a boundary. This is classic boundary
  value analysis driven by the code's own constants.
* :class:`SpecialValueStrategy` -- injects control-flow-flipping special values
  (zero, sign flip, very small / very large, and optionally non-finite) and
  ensures vectors contain a sign/zero mix, to trip ``is None`` / ``== 0`` /
  ``< 0`` / empty-vs-nonempty style branches.
"""

from __future__ import annotations

import math
from typing import List, Optional

from .base import Number, PerturbationContext, PerturbationStrategy


def _coerce_like(values: List[Number], pool: List[float]) -> List[Number]:
    """Cast pool elements to int when the original vector is integral."""
    is_float = any(isinstance(v, float) for v in values)
    if is_float:
        return [round(float(x), 8) for x in pool]
    return [int(round(x)) for x in pool]


class ThresholdStraddleStrategy(PerturbationStrategy):
    """Straddle the code's comparison constants (boundary value analysis)."""

    name = "threshold_straddle"

    def __init__(self, magnitude: float = 1.0, delta: float = 0.05, max_thresholds: int = 4) -> None:
        self.magnitude = magnitude
        self.delta = delta
        self.max_thresholds = max_thresholds

    def _usable(self, ctx: PerturbationContext) -> List[float]:
        return [t for t in sorted(set(ctx.thresholds)) if math.isfinite(t) and abs(t) < 1e9]

    def perturb_sequence(self, values: List[Number], ctx: PerturbationContext) -> Optional[List[Number]]:
        ts = self._usable(ctx)
        if not ts:
            return None

        if ctx.preserve_length:
            # Assign positions to thresholds round-robin and straddle each, keeping
            # the vector length (so shape-coupled arrays stay valid). Cycling over
            # thresholds means different positions exercise different boundaries.
            out_vals: List[float] = []
            for i, _v in enumerate(values):
                t = ts[i % len(ts)]
                d = self.delta * (abs(t) if t != 0 else 1.0)
                out_vals.append(ctx.rng.choice([t - d, t, t + d]))
            out = _coerce_like(values, out_vals)
            return out if out != list(values) else None

        # Resizing mode: replace with a spread that straddles every threshold.
        spread: List[float] = []
        for t in ts[: self.max_thresholds]:
            d = self.delta * (abs(t) if t != 0 else 1.0)
            spread.extend([t - d, t, t + d])
        peak = max((abs(t) for t in ts), default=1.0) or 1.0
        spread.extend([0.0, -peak - 1.0, peak * 2.0 + 1.0])  # zero / clear neg / large

        out = _coerce_like(values, spread)
        ctx.rng.shuffle(out)
        return out if out != list(values) else None

    def perturb_constant(self, value: Number, ctx: PerturbationContext) -> Optional[Number]:
        ts = self._usable(ctx)
        if not ts:
            return None
        t = ctx.rng.choice(ts)
        d = self.delta * (abs(t) if t != 0 else 1.0)
        cand = ctx.rng.choice([t - d, t, t + d])
        if isinstance(value, int) and not isinstance(value, bool):
            cand = int(round(cand))
        else:
            cand = round(float(cand), 8)
        return cand if cand != value else None


class SpecialValueStrategy(PerturbationStrategy):
    """Inject edge-case special values to trip common branches."""

    name = "special_value"

    def __init__(self, magnitude: float = 1.0, allow_nonfinite: bool = False, big: float = 1e6) -> None:
        self.magnitude = magnitude
        self.allow_nonfinite = allow_nonfinite
        self.big = big

    def _float_pool(self, value: float) -> List[float]:
        pool = [0.0, -value, value / self.big if value else 1e-6, value * self.big if value else self.big]
        if self.allow_nonfinite:
            pool += [math.inf, -math.inf, math.nan]
        return pool

    def _int_pool(self, value: int) -> List[int]:
        return [0, -value, value + 1, int(self.big)]

    def perturb_constant(self, value: Number, ctx: PerturbationContext) -> Optional[Number]:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        pool = self._float_pool(value) if isinstance(value, float) else self._int_pool(value)
        cand = ctx.rng.choice(pool)
        if isinstance(cand, float):
            cand = cand if not math.isfinite(cand) else round(cand, 8)
        return cand if cand != value else None

    def perturb_sequence(self, values: List[Number], ctx: PerturbationContext) -> Optional[List[Number]]:
        if not values:
            return None
        peak = max((abs(v) for v in values), default=1.0) or 1.0
        specials = [0.0, -peak, peak * self.big]  # zero, clear negative, large positive

        if ctx.preserve_length:
            # Overwrite a few elements in place with special values (keep count).
            out = list(values)
            k = min(len(out), len(specials))
            for idx, s in zip(ctx.rng.sample(range(len(out)), k), specials[:k]):
                out[idx] = s
            out = _coerce_like(values, out)
            return out if out != list(values) else None

        # Resizing mode: append special values.
        return list(values) + _coerce_like(values, specials)
