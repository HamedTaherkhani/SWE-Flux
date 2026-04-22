#!/usr/bin/env python3
"""
Drive matplotlib mathtext through a deeply nested \\frac expression so that
Parser.parse builds a tall box tree and ship()/hlist_out/vlist_out recurse deeply.
"""
import os
import sys
from pathlib import Path

# Load matplotlib from the repository under test (not an installed wheel).
_testbed_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_testbed_root / "lib"))
os.environ.setdefault("MPLBACKEND", "Agg")

from matplotlib.mathtext import MathTextParser  # noqa: E402


def _nested_frac_expr(depth: int) -> str:
    """Build \\frac{\\frac{...}{y}}{y} ... with fixed depth (valid mathtext)."""
    if depth <= 0:
        return "x"
    return r"\frac{" + _nested_frac_expr(depth - 1) + "}{y}"


class TestMathtextNestedFracShipMaxCallDepthQA:
    def test_mathtext_nested_frac_ship_max_call_depth_case(self):
        # 24 levels of nesting stresses pyparsing, box construction, and the
        # mutually recursive ship()/hlist_out/vlist_out walk in _mathtext.ship.
        expr = _nested_frac_expr(24)
        parser = MathTextParser("path")
        parser.parse(expr, dpi=96)
