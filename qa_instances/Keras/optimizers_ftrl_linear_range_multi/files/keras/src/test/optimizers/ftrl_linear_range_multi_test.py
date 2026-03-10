import numpy as np

from keras.src import backend
from keras.src import testing
from keras.src.optimizers.ftrl import Ftrl


class FtrlLinearRangeMultiQATest(testing.TestCase):
    def _run_scenario(
        self,
        learning_rate,
        learning_rate_power,
        initial_accumulator_value,
        l1_regularization_strength,
        l2_regularization_strength,
        l2_shrinkage_regularization_strength,
        beta,
        grad_steps,
    ):
        optimizer = Ftrl(
            learning_rate=learning_rate,
            learning_rate_power=learning_rate_power,
            initial_accumulator_value=initial_accumulator_value,
            l1_regularization_strength=l1_regularization_strength,
            l2_regularization_strength=l2_regularization_strength,
            l2_shrinkage_regularization_strength=l2_shrinkage_regularization_strength,
            beta=beta,
        )
        v1 = backend.Variable(np.array([1.0, -0.5, 0.3], dtype="float32"), name="ftrl_v1")
        v2 = backend.Variable(np.array([-0.2, 0.7, -1.1], dtype="float32"), name="ftrl_v2")

        for g1, g2 in grad_steps:
            grads = [
                np.array(g1, dtype="float32"),
                np.array(g2, dtype="float32"),
            ]
            optimizer.apply(grads, [v1, v2])

        return v1, v2

    def test_range_case_01(self):
        v1, v2 = self._run_scenario(
            0.05,
            -0.2,
            0.4,
            0.05,
            0.15,
            0.01,
            0.3,
            [
                ([0.1, 0.2, 0.3], [-0.2, 0.1, 0.0]),
                ([0.2, -0.1, 0.4], [0.3, -0.2, 0.1]),
                ([-0.3, 0.2, -0.2], [0.0, 0.4, -0.1]),
            ],
        )
        self.assertEqual(tuple(v1.shape), (3,))
        self.assertEqual(tuple(v2.shape), (3,))

    def test_range_case_02(self):
        v1, v2 = self._run_scenario(
            0.08,
            -0.5,
            0.2,
            0.02,
            0.10,
            0.0,
            0.0,
            [
                ([1.0, -0.5, 0.7], [0.5, -0.3, 0.2]),
                ([0.9, 0.2, -0.6], [-0.4, 0.8, -0.1]),
                ([1.2, -0.9, 0.4], [0.6, -0.7, 0.3]),
                ([-0.8, 0.5, -0.2], [-0.1, 0.2, -0.4]),
            ],
        )
        self.assertEqual(tuple(v1.shape), (3,))
        self.assertEqual(tuple(v2.shape), (3,))

    def test_range_case_03(self):
        v1, v2 = self._run_scenario(
            0.02,
            -0.25,
            0.5,
            0.1,
            0.2,
            0.03,
            0.6,
            [
                ([0.01, 0.02, 0.03], [0.02, 0.01, -0.01]),
                ([0.03, -0.02, 0.01], [0.00, 0.04, -0.02]),
                ([0.02, 0.03, -0.01], [0.01, -0.03, 0.02]),
                ([-0.01, 0.00, 0.02], [0.03, 0.02, -0.01]),
            ],
        )
        self.assertEqual(tuple(v1.shape), (3,))
        self.assertEqual(tuple(v2.shape), (3,))

    def test_range_case_04(self):
        v1, v2 = self._run_scenario(
            0.12,
            -0.1,
            0.3,
            0.0,
            0.25,
            0.02,
            0.4,
            [
                ([2.0, -1.0, 1.5], [-1.2, 0.8, -0.6]),
                ([1.8, 0.5, -1.1], [0.7, -0.9, 1.0]),
                ([-1.5, 1.2, -0.7], [0.3, 1.1, -0.8]),
            ],
        )
        self.assertEqual(tuple(v1.shape), (3,))
        self.assertEqual(tuple(v2.shape), (3,))

    def test_range_case_05(self):
        v1, v2 = self._run_scenario(
            0.04,
            -0.4,
            0.1,
            0.08,
            0.05,
            0.01,
            0.2,
            [
                ([0.4, 0.4, 0.4], [0.4, 0.4, 0.4]),
                ([-0.4, -0.4, -0.4], [-0.3, -0.2, -0.1]),
                ([0.2, -0.2, 0.2], [0.1, -0.1, 0.3]),
                ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]),
            ],
        )
        self.assertEqual(tuple(v1.shape), (3,))
        self.assertEqual(tuple(v2.shape), (3,))

    def test_range_case_06(self):
        v1, v2 = self._run_scenario(
            0.06,
            -0.3,
            0.6,
            0.03,
            0.12,
            0.02,
            0.1,
            [
                ([3.0, -2.0, 1.0], [-2.0, 1.0, -3.0]),
                ([2.5, -1.5, 0.5], [-1.5, 0.5, -2.5]),
                ([-2.0, 1.0, -0.5], [1.0, -0.5, 2.0]),
                ([1.5, -0.8, 0.3], [-0.7, 0.4, -1.1]),
            ],
        )
        self.assertEqual(tuple(v1.shape), (3,))
        self.assertEqual(tuple(v2.shape), (3,))

    def test_range_case_07(self):
        v1, v2 = self._run_scenario(
            0.03,
            -0.2,
            0.9,
            0.15,
            0.05,
            0.04,
            0.5,
            [
                ([0.6, 0.0, -0.6], [0.5, -0.5, 0.5]),
                ([0.7, -0.1, -0.5], [0.4, -0.4, 0.4]),
                ([0.5, 0.2, -0.7], [0.3, -0.3, 0.3]),
            ],
        )
        self.assertEqual(tuple(v1.shape), (3,))
        self.assertEqual(tuple(v2.shape), (3,))

    def test_range_case_08(self):
        v1, v2 = self._run_scenario(
            0.09,
            -0.45,
            0.15,
            0.01,
            0.18,
            0.0,
            0.0,
            [
                ([0.3, -0.9, 1.2], [1.1, -0.2, 0.6]),
                ([0.2, -0.8, 1.0], [0.9, -0.1, 0.5]),
                ([0.1, -0.7, 0.8], [0.7, 0.0, 0.4]),
                ([0.0, -0.6, 0.6], [0.5, 0.1, 0.3]),
                ([-0.1, -0.5, 0.4], [0.3, 0.2, 0.2]),
            ],
        )
        self.assertEqual(tuple(v1.shape), (3,))
        self.assertEqual(tuple(v2.shape), (3,))

    def test_range_case_09(self):
        v1, v2 = self._run_scenario(
            0.07,
            -0.35,
            0.25,
            0.06,
            0.09,
            0.03,
            0.7,
            [
                ([1.5, 1.0, 0.5], [-1.0, -0.5, 0.0]),
                ([-1.2, -0.8, -0.4], [0.8, 0.4, 0.0]),
                ([1.0, 0.6, 0.2], [-0.6, -0.2, 0.2]),
                ([-0.8, -0.4, 0.0], [0.4, 0.0, 0.4]),
            ],
        )
        self.assertEqual(tuple(v1.shape), (3,))
        self.assertEqual(tuple(v2.shape), (3,))

    def test_range_case_10(self):
        v1, v2 = self._run_scenario(
            0.11,
            -0.15,
            0.35,
            0.04,
            0.22,
            0.02,
            0.9,
            [
                ([4.0, -3.0, 2.0], [-3.0, 2.0, -1.0]),
                ([3.5, -2.5, 1.5], [-2.5, 1.5, -0.5]),
                ([3.0, -2.0, 1.0], [-2.0, 1.0, 0.0]),
            ],
        )
        self.assertEqual(tuple(v1.shape), (3,))
        self.assertEqual(tuple(v2.shape), (3,))

    def test_range_case_11(self):
        v1, v2 = self._run_scenario(
            0.025,
            -0.5,
            0.75,
            0.12,
            0.08,
            0.05,
            0.15,
            [
                ([0.05, 0.10, 0.15], [0.20, 0.25, 0.30]),
                ([0.10, 0.05, 0.00], [0.15, 0.10, 0.05]),
                ([0.00, -0.05, -0.10], [0.05, 0.00, -0.05]),
                ([-0.10, -0.15, -0.20], [-0.05, -0.10, -0.15]),
                ([-0.05, 0.00, 0.05], [0.00, 0.05, 0.10]),
            ],
        )
        self.assertEqual(tuple(v1.shape), (3,))
        self.assertEqual(tuple(v2.shape), (3,))

    def test_range_case_12(self):
        v1, v2 = self._run_scenario(
            0.065,
            -0.28,
            0.18,
            0.09,
            0.14,
            0.06,
            0.25,
            [
                ([0.9, -0.4, 0.2], [-0.8, 0.3, -0.1]),
                ([0.7, -0.3, 0.1], [-0.6, 0.2, 0.0]),
                ([0.5, -0.2, 0.0], [-0.4, 0.1, 0.1]),
                ([0.3, -0.1, -0.1], [-0.2, 0.0, 0.2]),
                ([0.1, 0.0, -0.2], [0.0, -0.1, 0.3]),
                ([-0.1, 0.1, -0.3], [0.2, -0.2, 0.4]),
            ],
        )
        self.assertEqual(tuple(v1.shape), (3,))
        self.assertEqual(tuple(v2.shape), (3,))
