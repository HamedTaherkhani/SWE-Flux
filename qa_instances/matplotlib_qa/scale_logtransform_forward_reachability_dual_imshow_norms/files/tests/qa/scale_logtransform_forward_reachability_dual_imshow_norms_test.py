#!/usr/bin/env python3
"""
Side-by-side `imshow`: linear `Normalize` (no log transform) vs `LogNorm`
(log-scaled normalization), which composes a `LogScale` / `LogTransform` chain.
"""
import importlib
import os
import sys
from pathlib import Path

_testbed_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_testbed_root / "lib"))
os.environ.setdefault("MPLBACKEND", "Agg")

_plt = importlib.import_module("matplotlib.pyplot")
_mc = importlib.import_module("matplotlib.colors")
_np = importlib.import_module("numpy")


class TestScaleLogtransformForwardReachabilityDualImshowNormsQA:
    def test_scale_logtransform_forward_reachability_dual_imshow_norms_case(self):
        rng = _np.random.default_rng(7)
        z = rng.random((10, 12)) * 50 + 0.05
        fig, axes = _plt.subplots(1, 2)
        axes[0].imshow(z, norm=_mc.Normalize())
        axes[1].imshow(z, norm=_mc.LogNorm())
        _plt.close(fig)
