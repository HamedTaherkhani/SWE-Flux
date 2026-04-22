#!/usr/bin/env python3
"""
Rotating-field streamplot: RK integration repeatedly samples the velocity grid via
`streamplot.interpgrid`, producing a large, deterministic call count.
"""
import importlib
import os
import sys
from pathlib import Path

_testbed_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_testbed_root / "lib"))
os.environ.setdefault("MPLBACKEND", "Agg")

np = importlib.import_module("numpy")
plt = importlib.import_module("matplotlib.pyplot")


class TestStreamplotRotatingInterpgridCallFrequencyQA:
    def test_streamplot_rotating_interpgrid_call_frequency_case(self):
        """
        Uniform 10x10 grid on [-2, 2]^2, velocity (u, v) = (-y, x), density=0.8.
        Fixed parameters so `interpgrid` invocation count is stable across runs.
        """
        x = np.linspace(-2.0, 2.0, 10)
        X, Y = np.meshgrid(x, x)
        U = -Y
        V = X
        fig, ax = plt.subplots()
        ax.streamplot(
            X,
            Y,
            U,
            V,
            density=0.8,
            broken_streamlines=True,
        )
        plt.close(fig)
