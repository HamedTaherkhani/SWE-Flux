#!/usr/bin/env python3
"""
Local matplotlib only (sys.path + importlib). Multiple tests document
`composite_transform_factory` branches; the benchmark traces only
`test_composite_transform_factory_line_path_determinism_case` (eval.sh).
"""
import importlib
import os
import sys
from pathlib import Path

_testbed_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_testbed_root / "lib"))
os.environ.setdefault("MPLBACKEND", "Agg")

_tr = importlib.import_module("matplotlib.transforms")


def _qa_a():
    """Non-identity Affine2D: hits Affine2D+Affine2D branch (not Identity shortcut)."""
    return (
        _tr.Affine2D()
        .rotate_deg(-12.0)
        .scale(0.5, 2.0)
        .translate(1.0, -2.0)
    )


def _qa_b():
    return (
        _tr.Affine2D()
        .skew_deg(5.0, -3.0)
        .rotate_deg(40.0)
        .translate(0.25, 0.25)
    )


class TestCompositeTransformFactoryLinePathSupport:
    """Not executed by the QA eval loop."""

    def test_identity_left_returns_right_operand(self):
        i = _tr.IdentityTransform()
        right = _tr.Affine2D().scale(2.0, 3.0)
        out = _tr.composite_transform_factory(i, right)
        assert out is right

    def test_identity_right_returns_left_operand(self):
        left = _tr.Affine2D().translate(4.0, -1.0)
        i = _tr.IdentityTransform()
        out = _tr.composite_transform_factory(left, i)
        assert out is left

    def test_two_identity_returns_second_argument(self):
        i0 = _tr.IdentityTransform()
        i1 = _tr.IdentityTransform()
        out = _tr.composite_transform_factory(i0, i1)
        assert out is i1

    def test_identity_left_with_composite_affine_returns_composite(self):
        i = _tr.IdentityTransform()
        comp = _tr.composite_transform_factory(
            _tr.Affine2D().scale(2.0, 2.0),
            _tr.Affine2D().translate(1.0, 1.0),
        )
        out = _tr.composite_transform_factory(i, comp)
        assert out is comp

    def test_two_affine2d_yields_composite_affine2d(self):
        a = _tr.Affine2D().rotate_deg(7.0)
        b = _tr.Affine2D().scale(1.5, 0.5)
        out = _tr.composite_transform_factory(a, b)
        assert isinstance(out, _tr.CompositeAffine2D)

    def test_composite_affine2d_retains_child_references(self):
        a = _tr.Affine2D().translate(0.5, -0.5)
        b = _tr.Affine2D().rotate_deg(22.0)
        out = _tr.composite_transform_factory(a, b)
        assert out._a is a and out._b is b

    def test_add_operator_matches_factory_for_two_affine2d(self):
        a = _tr.Affine2D().scale(1.0, 2.0)
        b = _tr.Affine2D().translate(3.0, -1.0)
        via_add = a + b
        via_factory = _tr.composite_transform_factory(a, b)
        assert type(via_add) is type(via_factory)

    def test_affine2d_plus_transform_wrapper_uses_composite_generic(self):
        a = _tr.Affine2D().rotate_deg(5.0)
        wrapped = _tr.TransformWrapper(_tr.Affine2D().scale(2.0, 1.0))
        out = _tr.composite_transform_factory(a, wrapped)
        assert isinstance(out, _tr.CompositeGenericTransform)
        assert not isinstance(out, _tr.CompositeAffine2D)

    def test_wrapper_plus_affine2d_uses_composite_generic(self):
        wrapped = _tr.TransformWrapper(_tr.Affine2D().translate(1.0, 0.0))
        b = _tr.Affine2D().scale(0.5, 0.5)
        out = _tr.composite_transform_factory(wrapped, b)
        assert isinstance(out, _tr.CompositeGenericTransform)

    def test_qa_operands_are_affine2d(self):
        assert isinstance(_qa_a(), _tr.Affine2D)
        assert isinstance(_qa_b(), _tr.Affine2D)

    def test_qa_operands_have_two_dimensions(self):
        a, b = _qa_a(), _qa_b()
        assert a.input_dims == a.output_dims == 2
        assert b.input_dims == b.output_dims == 2

    def test_qa_branch_is_composite_affine_not_identity_shortcut(self):
        a, b = _qa_a(), _qa_b()
        assert not isinstance(a, _tr.IdentityTransform)
        assert not isinstance(b, _tr.IdentityTransform)
        out = _tr.composite_transform_factory(a, b)
        assert isinstance(out, _tr.CompositeAffine2D)

    def test_qa_composite_is_not_identity_transform(self):
        out = _tr.composite_transform_factory(_qa_a(), _qa_b())
        assert not isinstance(out, _tr.IdentityTransform)

    def test_skew_chain_still_subclass_affine2d(self):
        t = _tr.Affine2D().skew_deg(2.0, -1.0).rotate_deg(11.0)
        assert isinstance(t, _tr.Affine2D)


class TestCompositeTransformFactoryLinePathDeterminismQA:
    def test_composite_transform_factory_line_path_determinism_case(self):
        out = _tr.composite_transform_factory(_qa_a(), _qa_b())
        assert isinstance(out, _tr.CompositeAffine2D)
        assert out.is_affine
