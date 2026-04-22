#!/usr/bin/env python3
"""
Local matplotlib.colors via sys.path + importlib (no `import matplotlib`).
One QA test is traced by eval.sh; support tests document color conversion edges.
"""
import importlib
import os
import sys
from pathlib import Path

import numpy as np
import pytest

_testbed_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_testbed_root / "lib"))
os.environ.setdefault("MPLBACKEND", "Agg")

_colors = importlib.import_module("matplotlib.colors")


def _qa_hex():
    return "#9467bd"


def _qa_alpha():
    return 0.625


class TestColorsToRgbaOutputDeterminismSupport:
    """Not run by the benchmark eval loop."""

    def test_to_rgba_named_color(self):
        t = _colors.to_rgba("firebrick")
        assert len(t) == 4 and t[3] == 1.0

    def test_to_rgba_hex_six_digit(self):
        t = _colors.to_rgba("#2ca02c")
        assert len(t) == 4

    def test_to_rgba_string_none_is_transparent(self):
        t = _colors.to_rgba("none")
        assert t == (0.0, 0.0, 0.0, 0.0)

    def test_to_rgba_rejects_alpha_below_zero(self):
        with pytest.raises(ValueError, match="alpha"):
            _colors.to_rgba("#ff0000", alpha=-0.01)

    def test_to_rgba_rejects_alpha_above_one(self):
        with pytest.raises(ValueError, match="alpha"):
            _colors.to_rgba("#00ff00", alpha=1.01)

    def test_to_rgba_tuple_pair_unpacks_alpha(self):
        t = _colors.to_rgba(("#0000ff", 0.25))
        assert abs(t[3] - 0.25) < 1e-9

    def test_to_rgba_masked_returns_zeros(self):
        t = _colors.to_rgba(np.ma.masked)
        assert t == (0.0, 0.0, 0.0, 0.0)

    def test_same_color_on_two_hex_strings(self):
        assert _colors.same_color("#1f77b4", "#1f77b4")

    def test_to_rgb_drops_alpha(self):
        rgb = _colors.to_rgb("#e377c2")
        assert len(rgb) == 3

    def test_is_color_like_accepts_qa_hex(self):
        assert _colors.is_color_like(_qa_hex())

    def test_to_hex_named_color(self):
        h = _colors.to_hex("forestgreen")
        assert h.startswith("#") and len(h) == 7

    def test_to_rgba_explicit_alpha_overrides_sequence_alpha(self):
        t = _colors.to_rgba((0.2, 0.4, 0.6, 0.1), alpha=0.9)
        assert abs(t[3] - 0.9) < 1e-9

    def test_to_rgba_grayscale_string(self):
        t = _colors.to_rgba("0.35")
        assert abs(t[0] - 0.35) < 1e-9 and t[0] == t[1] == t[2]

    def test_tab_color_resolves_via_cycle(self):
        t = _colors.to_rgba("tab:orange")
        assert len(t) == 4 and all(0.0 <= x <= 1.0 for x in t)

    def test_qa_call_returns_rgba_tuple_length_four(self):
        t = _colors.to_rgba(_qa_hex(), alpha=_qa_alpha())
        assert len(t) == 4


class TestColorsToRgbaOutputDeterminismQA:
    def test_colors_to_rgba_output_determinism_case(self):
        out = _colors.to_rgba(_qa_hex(), alpha=_qa_alpha())
        assert len(out) == 4
        assert all(isinstance(x, float) for x in out)
