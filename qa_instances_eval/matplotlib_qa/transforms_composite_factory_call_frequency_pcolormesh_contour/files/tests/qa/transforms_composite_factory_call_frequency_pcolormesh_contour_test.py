#!/usr/bin/env python3
"""
Single axes with `pcolormesh` then `contour` on fixed RNG meshes — composes many
transforms (data, axes, bbox, padding) via `composite_transform_factory` internally.
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


class TestTransformsCompositeFactoryCallFrequencyPcolormeshContourQA:
    def test_transforms_composite_factory_call_frequency_pcolormesh_contour_case(self):
        fig, ax = _plt.subplots()
        ax.pcolormesh(_np.random.default_rng(1).random((15, 20)))
        ax.contour(_np.random.default_rng(2).random((15, 20)), levels=5)
        _plt.close(fig)
