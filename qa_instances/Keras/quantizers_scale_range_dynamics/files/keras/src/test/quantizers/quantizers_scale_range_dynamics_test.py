import numpy as np

from keras.src import ops
from keras.src import testing
from keras.src.quantizers import quantizers


class QuantizersScaleRangeDynamicsQATest(testing.TestCase):
    def _run_case(self, num_bits, narrow_range, min_max_pairs):
        scales = []
        for min_range, max_range in min_max_pairs:
            _, _, scale, _ = quantizers.adjust_and_nudge(
                np.array(min_range, dtype="float32"),
                np.array(max_range, dtype="float32"),
                num_bits=num_bits,
                narrow_range=narrow_range,
            )
            scales.append(float(ops.convert_to_numpy(scale)))
        self.assertEqual(len(scales), len(min_max_pairs))
        self.assertGreater(scales[-1], 0.0)

    def test_case_01(self):
        self._run_case(
            8,
            False,
            [(-0.5, 0.5), (-0.6, 0.8), (-0.8, 1.1), (-1.0, 1.5)],
        )

    def test_case_02(self):
        self._run_case(
            8,
            True,
            [(-0.4, 0.6), (-0.7, 0.9), (-1.0, 1.3), (-1.3, 1.8)],
        )

    def test_case_03(self):
        self._run_case(
            7,
            False,
            [(-0.2, 0.4), (-0.4, 0.7), (-0.7, 1.2), (-1.1, 1.8)],
        )

    def test_case_04(self):
        self._run_case(
            6,
            False,
            [(-0.3, 0.3), (-0.5, 0.7), (-0.8, 1.1), (-1.2, 1.7)],
        )

    def test_case_05(self):
        self._run_case(
            6,
            True,
            [(-0.2, 0.5), (-0.5, 0.9), (-0.9, 1.4), (-1.5, 2.1)],
        )

    def test_case_06(self):
        self._run_case(
            5,
            False,
            [(-0.1, 0.2), (-0.2, 0.6), (-0.6, 1.0), (-1.0, 1.7)],
        )

    def test_case_07(self):
        self._run_case(
            5,
            True,
            [(-0.3, 0.4), (-0.6, 0.8), (-1.0, 1.3), (-1.4, 2.0)],
        )

    def test_case_08(self):
        self._run_case(
            4,
            False,
            [(-0.2, 0.3), (-0.4, 0.7), (-0.9, 1.2), (-1.5, 2.2)],
        )

    def test_case_09(self):
        self._run_case(
            8,
            False,
            [(-0.9, 0.1), (-1.1, 0.5), (-1.4, 0.9), (-1.8, 1.5)],
        )

    def test_case_10(self):
        self._run_case(
            8,
            True,
            [(-0.7, 0.2), (-0.9, 0.6), (-1.3, 1.1), (-1.9, 1.9)],
        )

    def test_case_11(self):
        self._run_case(
            7,
            True,
            [(-0.4, 0.3), (-0.8, 0.7), (-1.2, 1.2), (-1.7, 1.8)],
        )

    def test_case_12(self):
        self._run_case(
            6,
            False,
            [(-0.6, 0.2), (-0.9, 0.7), (-1.3, 1.3), (-2.0, 2.1)],
        )
