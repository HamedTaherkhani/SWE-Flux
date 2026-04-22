#!/usr/bin/env python3
"""
SymmetricalLogLocator.tick_values: strided decade assembly, optional linear segment,
and subs-expanded tick multiplication — complex control flow before the
`for decade in decades:` loop (local source only; no `import matplotlib`).

Loads the ticker implementation from the repo lib/ tree so the trace reflects
this checkout, not a pre-installed wheel.
"""
import sys
from pathlib import Path

_testbed_root = Path(__file__).resolve()
for _ in range(12):
    if (_testbed_root / "lib" / "matplotlib").is_dir():
        break
    _testbed_root = _testbed_root.parent
else:
    raise RuntimeError("Could not locate testbed/lib/matplotlib from %s" % (__file__,))
if str(_testbed_root / "lib") not in sys.path:
    sys.path.insert(0, str(_testbed_root / "lib"))

import importlib

_ticker = importlib.import_module("matplotlib.ticker")
SymmetricalLogLocator = _ticker.SymmetricalLogLocator


class TestTickerSymlogDecadeLoopIterationsQA:
    def test_ticker_symlog_decade_loop_iterations_case(self):
        """
        Drive `SymmetricalLogLocator.tick_values` with a range spanning negative
        quasi-log decades, the linear corridor, and positive decades, with
        non-trivial stride thinning and multi-valued subs — so `decades` is long
        and the subs branch executes a nontrivial loop at ticker.py ~2640.
        """
        loc = SymmetricalLogLocator(linthresh=0.5, base=10, subs=(1.0, 2.0, 5.0))
        loc.numticks = 9
        loc.tick_values(-2000.0, 8000.0)
