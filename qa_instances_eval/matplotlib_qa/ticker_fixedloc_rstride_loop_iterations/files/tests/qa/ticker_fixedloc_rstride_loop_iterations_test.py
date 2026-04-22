#!/usr/bin/env python3
"""
FixedLocator.tick_values: when *nbins* is set, subsampling picks a stride and then
iterates `for i in range(1, step):`, shifting phase to minimize |tick| among
candidates — non-sequential control flow with a data-dependent inner minimum.

Loads mpl from repo lib/ (no `import matplotlib`).
"""
import sys
from pathlib import Path

import numpy as np

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
FixedLocator = _ticker.FixedLocator


class TestTickerFixedlocRstrideLoopIterationsQA:
    def test_ticker_fixedloc_rstride_loop_iterations_case(self):
        """
        89 candidate ticks spanning a skewed interval; nbins=12 forces a stride
        from ceil(len(locs)/nbins) and a nontrivial inner `range(1, step)`.
        """
        rng = np.random.default_rng(42)
        # Non-uniform: two-scale spacing + jitter so |.| minima are not obvious.
        left = np.cumsum(rng.uniform(0.4, 2.1, size=40)) - 73.0
        right = np.cumsum(rng.uniform(0.3, 1.9, size=49)) + 2.0
        locs = np.unique(np.concatenate([left, right]))
        locs.sort()

        assert len(locs) == 89

        loc = FixedLocator(locs, nbins=12)
        loc.tick_values(None, None)
