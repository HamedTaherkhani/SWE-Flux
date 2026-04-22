#!/usr/bin/env python3
"""
Two MaxNLocator configurations: float range with explicit steps, then integer mode
with default staircase — exercises tick_values -> _raw_ticks -> scale_range and
_Edge_integer le/ge, then raise_if_exceeds, twice in sequence.
"""
import importlib
import os
import sys
from pathlib import Path

_testbed_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_testbed_root / "lib"))
os.environ.setdefault("MPLBACKEND", "Agg")

_mt = importlib.import_module("matplotlib.ticker")


class TestMaxnlocatorTickValuesFunctionCallOrderDualQA:
    def test_maxnlocator_tick_values_function_call_order_dual_case(self):
        loc_float = _mt.MaxNLocator(
            nbins=5,
            integer=False,
            steps=[1, 2, 5, 10],
        )
        loc_float.tick_values(10.0, 99.0)

        loc_int = _mt.MaxNLocator(
            nbins=8,
            integer=True,
            min_n_ticks=3,
        )
        loc_int.tick_values(11, 107)
