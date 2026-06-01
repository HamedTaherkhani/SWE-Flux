from __future__ import annotations

import numpy as np
import pytest

from control.bdalg import combine_tf, split_tf
from control.xferfcn import TransferFunction, tf


class TestCombineTfSisoColumnQA:
    def test_siso_column_from_transfer_functions(self):
        s = tf("s")
        system = combine_tf(
            [[1 / (s + 1)], [s / (s + 2)], [(s + 3) / (s**2 + 4 * s + 5)]],
            name="siso_column",
        )

        assert system.noutputs == 3
        assert system.ninputs == 1


class TestCombineTfMixedStaticBlocksQA:
    def test_mixed_numpy_and_transfer_blocks(self):
        s = tf("s")
        system = combine_tf(
            [
                [np.eye(2), np.array([[0.0], [1.0]])],
                [np.array([[2.0, -1.0]]), 1 / (s + 3)],
            ],
            inputs=["u0", "u1", "u2"],
            outputs=["y0", "y1", "y2"],
            name="mixed_static",
        )

        assert system.noutputs == 3
        assert system.ninputs == 3


class TestCombineTfMimoBlocksQA:
    def test_mimo_transfer_function_blocks(self):
        left = TransferFunction(
            [[[1.0], [2.0]], [[3.0], [4.0]]],
            [[[1.0, 1.0], [1.0, 2.0]], [[1.0, 3.0], [1.0, 4.0]]],
        )
        right = TransferFunction(
            [[[5.0]], [[6.0]]],
            [[[1.0, 5.0]], [[1.0, 6.0]]],
        )
        system = combine_tf([[left, right]], name="mimo_blocks")

        assert system.noutputs == 2
        assert system.ninputs == 3


class TestCombineTfDiscreteQA:
    def test_discrete_time_blocks(self):
        zsys = tf([1.0, -0.2], [1.0, -0.7], dt=0.25)
        system = combine_tf(
            [[zsys, np.array([[0.5]])], [np.array([[1.0]]), zsys * 2]],
            name="discrete_combo",
        )

        assert system.dt == 0.25
        assert system.noutputs == 2
        assert system.ninputs == 2


class TestCombineTfNoneTimebaseQA:
    def test_unspecified_timebase_with_static_entries(self):
        system = combine_tf(
            [
                [TransferFunction([1.0], [1.0, 1.0], None), 2.0],
                [np.array([[0.0]]), TransferFunction([3.0], [1.0, 2.0], None)],
            ],
            name="none_timebase",
        )

        assert system.dt is None
        assert system.noutputs == 2


class TestCombineTfSplitRoundtripQA:
    def test_split_then_recombine(self):
        original = TransferFunction(
            [[[1.0, 1.0], [2.0]], [[3.0], [4.0, 1.0]]],
            [[[1.0, 2.0], [1.0, 3.0]], [[1.0, 4.0], [1.0, 5.0]]],
            name="original",
        )
        pieces = split_tf(original)
        rebuilt = combine_tf(pieces.tolist(), name="rebuilt")

        assert rebuilt.noutputs == original.noutputs
        assert rebuilt.ninputs == original.ninputs


class TestCombineTfZeroNumeratorQA:
    def test_zero_numerator_entries(self):
        s = tf("s")
        system = combine_tf(
            [[0, 1 / (s + 1)], [np.array([[0.0]]), (s + 2) / (s + 3)]],
            name="zero_num",
        )

        assert system.noutputs == 2
        assert system.ninputs == 2


class TestCombineTfNamedSignalsQA:
    def test_explicit_signal_labels(self):
        s = tf("s")
        system = combine_tf(
            [[1 / (s + 1), 2 / (s + 2)]],
            inputs=["force", "disturbance"],
            outputs=["position"],
            name="named_combo",
        )

        assert system.input_labels == ["force", "disturbance"]
        assert system.output_labels == ["position"]


class TestCombineTfTimebaseMismatchQA:
    def test_timebase_mismatch_is_caught(self):
        fast = tf([1.0], [1.0, -0.2], dt=0.1)
        slow = tf([1.0], [1.0, -0.3], dt=0.2)

        with pytest.raises(ValueError, match="Time steps"):
            combine_tf([[fast, slow]], name="bad_dt")


class TestCombineTfBadShapeQA:
    def test_bad_array_dimension_is_caught(self):
        cube = np.ones((1, 1, 2, 1))

        with pytest.raises(ValueError, match="less than two dimensions"):
            combine_tf([[cube]], name="bad_shape")
