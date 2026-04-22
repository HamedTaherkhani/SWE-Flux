#!/usr/bin/env python3
"""
Exercise matplotlib.colors._to_rgba_no_colorcycle string-grayscale branch so that
line 388 evaluates `if not (0 <= c <= 1):` after `c = float(c)`.
Loads the library from the repo via sys.path (no top-level `import matplotlib` statement).
"""
import importlib
import os
import sys
from pathlib import Path

_testbed_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_testbed_root / "lib"))
os.environ.setdefault("MPLBACKEND", "Agg")

_colors = importlib.import_module("matplotlib.colors")

# Distinct literal so trace parsing can pick this invocation among import-time calls.
# Every test in this class must use this exact string so the benchmark has a single oracle.
_GRAY = "0.371825413792"


def _assert_grayscale_rgba(rgba):
    assert rgba[0] == rgba[1] == rgba[2]
    assert abs(rgba[0] - float(_GRAY)) < 1e-12
    assert rgba[3] == 1.0


class TestColorsNocolorcycleGrayscaleIntervalConditionSnapshotQA:
    def test_direct_call(self):
        _assert_grayscale_rgba(_colors._to_rgba_no_colorcycle(_GRAY, None))

    def test_via_tuple_unpack_and_alias(self):
        s, a = (_GRAY, None)
        _assert_grayscale_rgba(_colors._to_rgba_no_colorcycle(s, a))

    def test_via_getattr(self):
        fn = getattr(_colors, "_to_rgba_no_colorcycle")
        _assert_grayscale_rgba(fn(_GRAY, None))

    def test_via_nested_scope_factory(self):
        def run(conv, g):
            return conv(g, None)

        _assert_grayscale_rgba(run(_colors._to_rgba_no_colorcycle, _GRAY))

    def test_via_string_dict_roundtrip(self):
        payload = {"g": "".join(list(_GRAY))}
        _assert_grayscale_rgba(_colors._to_rgba_no_colorcycle(payload["g"], None))

    def test_via_staticmethod_style_helper(self):
        def invoke(mod, gray_lit):
            return mod._to_rgba_no_colorcycle(gray_lit, None)

        _assert_grayscale_rgba(invoke(_colors, _GRAY))
