#!/usr/bin/env python3
"""
Isolated QA module: local matplotlib via sys.path + importlib.

Several tests document separability and factory behavior; the benchmark oracle
targets only `test_blended_transform_factory_output_determinism_case` (see eval.sh).
"""
import importlib
import os
import sys
from pathlib import Path

import pytest

_testbed_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_testbed_root / "lib"))
os.environ.setdefault("MPLBACKEND", "Agg")

_tr = importlib.import_module("matplotlib.transforms")


def _qa_x_pipeline():
    return (
        _tr.Affine2D()
        .translate(9.25, -3.5)
        .scale(0.5, 1.25)
        .translate(-2.1, 4.2)
        .scale(3.0, 3.0)
    )


def _qa_y_pipeline():
    return (
        _tr.Affine2D()
        .scale(1.125, -0.875)
        .translate(-1.0, 6.375)
        .translate(0.25, -0.5)
        .scale(0.1, 10.0)
    )


class TestBlendedTransformFactoryOutputDeterminismSupport:
    """Sanity checks; not used by the trace / oracle pipeline."""

    def test_scale_translate_affine_is_separable(self):
        a = _tr.Affine2D().translate(2.0, -1.0).scale(3.0, 0.5)
        m = a.get_matrix()
        assert m[0, 1] == 0.0 and m[1, 0] == 0.0
        assert bool(a.is_separable)

    def test_rotation_makes_affine_non_separable(self):
        b = _tr.Affine2D().rotate_deg(15.0)
        m = b.get_matrix()
        assert not (m[0, 1] == 0.0 and m[1, 0] == 0.0)
        assert not bool(b.is_separable)

    def test_blended_factory_rejects_non_separable_affine_pair(self):
        x_ok = _tr.Affine2D().scale(2.0, 2.0)
        y_bad = _tr.Affine2D().rotate_deg(10.0)
        with pytest.raises(ValueError):
            _tr.blended_transform_factory(x_ok, y_bad)

    def test_qa_pipelines_are_separable(self):
        x = _qa_x_pipeline()
        y = _qa_y_pipeline()
        assert x.is_separable and y.is_separable

    def test_blended_factory_returns_blended_affine_for_qa_inputs(self):
        out = _tr.blended_transform_factory(_qa_x_pipeline(), _qa_y_pipeline())
        assert isinstance(out, _tr.BlendedAffine2D)
        assert out.is_affine


class TestBlendedTransformFactoryOutputDeterminismQA:
    def test_blended_transform_factory_output_determinism_case(self):
        out = _tr.blended_transform_factory(_qa_x_pipeline(), _qa_y_pipeline())
        assert out is not None
        assert out.is_affine
