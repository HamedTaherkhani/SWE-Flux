#!/usr/bin/env python3
"""
Linear axes, then log-log axes, then symlog — only the log-log phase invokes
forward `LogTransform.transform_non_affine`; symlog uses `SymmetricalLogTransform`.
"""
import importlib
import os
import sys
from pathlib import Path

_testbed_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_testbed_root / "lib"))
os.environ.setdefault("MPLBACKEND", "Agg")

_plt = importlib.import_module("matplotlib.pyplot")
_np = importlib.import_module("numpy")


class TestScaleLogtransformForwardCallFrequencyTripleBranchQA:
    def test_scale_logtransform_forward_call_frequency_triple_branch_case(self):
        fig1, ax1 = _plt.subplots()
        ax1.plot([1, 2, 3], [3, 2, 1])
        _plt.close(fig1)

        rng = _np.random.default_rng(0)
        fig2, ax2 = _plt.subplots()
        ax2.plot(_np.linspace(0.01, 1000, 500), rng.random(500))
        ax2.set_xscale("log")
        ax2.set_yscale("log")
        _plt.close(fig2)

        fig3, ax3 = _plt.subplots()
        ax3.plot(_np.linspace(-3, 3, 40), _np.linspace(0.1, 10, 40))
        ax3.set_yscale("symlog", linthresh=0.2)
        _plt.close(fig3)
