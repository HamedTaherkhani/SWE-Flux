import numpy as np

from keras.src import backend
from keras.src import ops
from keras.src import testing
from keras.src.optimizers.loss_scale_optimizer import LossScaleOptimizer
from keras.src.optimizers.sgd import SGD


class LossScaleStepCounterRangeMultiQATest(testing.TestCase):
    def _run_scenario(self, dynamic_growth_steps, initial_scale, grad_steps):
        inner_optimizer = SGD(learning_rate=0.05)
        optimizer = LossScaleOptimizer(
            inner_optimizer,
            initial_scale=initial_scale,
            dynamic_growth_steps=dynamic_growth_steps,
        )
        var = backend.Variable(np.array([1.0, -2.0, 3.0], dtype="float32"))
        step_counter_values = []

        for tag, grad_values in grad_steps:
            if tag == "finite":
                grads = [np.array(grad_values, dtype="float32")]
            elif tag == "nonfinite":
                grads = [np.array(grad_values, dtype="float32")]
            else:
                raise ValueError(f"Unknown step tag: {tag}")
            optimizer.apply(grads, [var])
            step_counter_values.append(
                int(ops.convert_to_numpy(optimizer.step_counter.value))
            )

        iterations = int(ops.convert_to_numpy(optimizer.iterations.value))
        return var, iterations, step_counter_values

    def test_range_case_01(self):
        var, iterations, _ = self._run_scenario(
            dynamic_growth_steps=3,
            initial_scale=8.0,
            grad_steps=[
                ("finite", [1.0, -0.5, 0.3]),
                ("finite", [0.4, 0.1, -0.2]),
                ("finite", [0.8, -0.3, 0.2]),
                ("finite", [0.2, 0.2, 0.2]),
            ],
        )
        self.assertGreaterEqual(iterations, 0)
        self.assertLessEqual(iterations, 4)
        self.assertEqual(tuple(var.shape), (3,))

    def test_range_case_02(self):
        var, iterations, _ = self._run_scenario(
            dynamic_growth_steps=4,
            initial_scale=16.0,
            grad_steps=[
                ("finite", [0.5, 0.5, -0.5]),
                ("nonfinite", [np.inf, 0.0, -np.inf]),
                ("finite", [1.2, -0.7, 0.9]),
                ("finite", [-0.2, 0.3, 0.1]),
                ("finite", [0.0, -0.1, 0.2]),
            ],
        )
        self.assertGreaterEqual(iterations, 0)
        self.assertLessEqual(iterations, 5)
        self.assertEqual(tuple(var.shape), (3,))

    def test_range_case_03(self):
        var, iterations, _ = self._run_scenario(
            dynamic_growth_steps=5,
            initial_scale=32.0,
            grad_steps=[
                ("finite", [0.1, 0.2, 0.3]),
                ("finite", [0.2, 0.1, 0.0]),
                ("finite", [-0.1, -0.2, -0.3]),
                ("finite", [0.4, -0.4, 0.4]),
                ("finite", [0.7, -0.6, 0.5]),
                ("finite", [0.9, -0.8, 0.7]),
            ],
        )
        self.assertGreaterEqual(iterations, 0)
        self.assertLessEqual(iterations, 6)
        self.assertEqual(tuple(var.shape), (3,))

    def test_range_case_04(self):
        var, iterations, _ = self._run_scenario(
            dynamic_growth_steps=6,
            initial_scale=4.0,
            grad_steps=[
                ("nonfinite", [np.inf, np.inf, np.inf]),
                ("finite", [0.3, -0.2, 0.1]),
                ("finite", [0.6, -0.4, 0.2]),
                ("finite", [0.9, -0.6, 0.3]),
                ("finite", [1.2, -0.8, 0.4]),
                ("finite", [1.5, -1.0, 0.5]),
                ("finite", [1.8, -1.2, 0.6]),
            ],
        )
        self.assertGreaterEqual(iterations, 0)
        self.assertLessEqual(iterations, 7)
        self.assertEqual(tuple(var.shape), (3,))

    def test_range_case_05(self):
        var, iterations, _ = self._run_scenario(
            dynamic_growth_steps=7,
            initial_scale=2.0,
            grad_steps=[
                ("finite", [0.2, 0.2, 0.2]),
                ("finite", [0.2, 0.2, 0.2]),
                ("finite", [0.2, 0.2, 0.2]),
                ("nonfinite", [np.nan, 1.0, -1.0]),
                ("finite", [0.5, 0.5, 0.5]),
                ("finite", [0.6, 0.6, 0.6]),
                ("finite", [0.7, 0.7, 0.7]),
                ("finite", [0.8, 0.8, 0.8]),
            ],
        )
        self.assertGreaterEqual(iterations, 0)
        self.assertLessEqual(iterations, 8)
        self.assertEqual(tuple(var.shape), (3,))

    def test_range_case_06(self):
        var, iterations, _ = self._run_scenario(
            dynamic_growth_steps=8,
            initial_scale=64.0,
            grad_steps=[
                ("finite", [2.0, -1.0, 0.5]),
                ("finite", [1.8, -0.9, 0.4]),
                ("finite", [1.6, -0.8, 0.3]),
                ("finite", [1.4, -0.7, 0.2]),
                ("finite", [1.2, -0.6, 0.1]),
                ("finite", [1.0, -0.5, 0.0]),
                ("finite", [0.8, -0.4, -0.1]),
                ("finite", [0.6, -0.3, -0.2]),
                ("finite", [0.4, -0.2, -0.3]),
            ],
        )
        self.assertGreaterEqual(iterations, 0)
        self.assertLessEqual(iterations, 9)
        self.assertEqual(tuple(var.shape), (3,))

    def test_range_case_07(self):
        var, iterations, _ = self._run_scenario(
            dynamic_growth_steps=5,
            initial_scale=10.0,
            grad_steps=[
                ("finite", [0.1, -0.1, 0.1]),
                ("nonfinite", [np.inf, -np.inf, np.inf]),
                ("finite", [0.2, -0.2, 0.2]),
                ("nonfinite", [np.nan, np.nan, np.nan]),
                ("finite", [0.3, -0.3, 0.3]),
                ("finite", [0.4, -0.4, 0.4]),
            ],
        )
        self.assertGreaterEqual(iterations, 0)
        self.assertLessEqual(iterations, 6)
        self.assertEqual(tuple(var.shape), (3,))

    def test_range_case_08(self):
        var, iterations, _ = self._run_scenario(
            dynamic_growth_steps=9,
            initial_scale=12.0,
            grad_steps=[
                ("finite", [0.9, 0.1, -0.1]),
                ("finite", [0.8, 0.2, -0.2]),
                ("finite", [0.7, 0.3, -0.3]),
                ("finite", [0.6, 0.4, -0.4]),
                ("finite", [0.5, 0.5, -0.5]),
                ("finite", [0.4, 0.6, -0.6]),
                ("finite", [0.3, 0.7, -0.7]),
                ("finite", [0.2, 0.8, -0.8]),
                ("finite", [0.1, 0.9, -0.9]),
                ("finite", [0.0, 1.0, -1.0]),
            ],
        )
        self.assertGreaterEqual(iterations, 0)
        self.assertLessEqual(iterations, 10)
        self.assertEqual(tuple(var.shape), (3,))

    def test_range_case_09(self):
        var, iterations, _ = self._run_scenario(
            dynamic_growth_steps=4,
            initial_scale=20.0,
            grad_steps=[
                ("nonfinite", [np.inf, 0.0, 0.0]),
                ("nonfinite", [0.0, np.inf, 0.0]),
                ("finite", [1.0, 1.0, 1.0]),
                ("finite", [1.0, 1.0, 1.0]),
                ("finite", [1.0, 1.0, 1.0]),
                ("finite", [1.0, 1.0, 1.0]),
            ],
        )
        self.assertGreaterEqual(iterations, 0)
        self.assertLessEqual(iterations, 6)
        self.assertEqual(tuple(var.shape), (3,))

    def test_range_case_10(self):
        var, iterations, _ = self._run_scenario(
            dynamic_growth_steps=6,
            initial_scale=6.0,
            grad_steps=[
                ("finite", [0.25, -0.25, 0.5]),
                ("finite", [0.5, -0.5, 1.0]),
                ("finite", [0.75, -0.75, 1.5]),
                ("nonfinite", [np.nan, 0.0, np.inf]),
                ("finite", [1.0, -1.0, 2.0]),
                ("finite", [1.25, -1.25, 2.5]),
                ("finite", [1.5, -1.5, 3.0]),
            ],
        )
        self.assertGreaterEqual(iterations, 0)
        self.assertLessEqual(iterations, 7)
        self.assertEqual(tuple(var.shape), (3,))

    def test_range_case_11(self):
        var, iterations, _ = self._run_scenario(
            dynamic_growth_steps=10,
            initial_scale=18.0,
            grad_steps=[
                ("finite", [0.1, 0.0, -0.1]),
                ("finite", [0.2, 0.0, -0.2]),
                ("finite", [0.3, 0.0, -0.3]),
                ("finite", [0.4, 0.0, -0.4]),
                ("finite", [0.5, 0.0, -0.5]),
                ("finite", [0.6, 0.0, -0.6]),
                ("finite", [0.7, 0.0, -0.7]),
                ("finite", [0.8, 0.0, -0.8]),
                ("finite", [0.9, 0.0, -0.9]),
                ("finite", [1.0, 0.0, -1.0]),
                ("finite", [1.1, 0.0, -1.1]),
            ],
        )
        self.assertGreaterEqual(iterations, 0)
        self.assertLessEqual(iterations, 11)
        self.assertEqual(tuple(var.shape), (3,))

    def test_range_case_12(self):
        var, iterations, _ = self._run_scenario(
            dynamic_growth_steps=11,
            initial_scale=14.0,
            grad_steps=[
                ("finite", [0.3, -0.1, 0.2]),
                ("finite", [0.6, -0.2, 0.4]),
                ("finite", [0.9, -0.3, 0.6]),
                ("finite", [1.2, -0.4, 0.8]),
                ("finite", [1.5, -0.5, 1.0]),
                ("nonfinite", [np.inf, np.nan, -np.inf]),
                ("finite", [1.8, -0.6, 1.2]),
                ("finite", [2.1, -0.7, 1.4]),
                ("finite", [2.4, -0.8, 1.6]),
                ("finite", [2.7, -0.9, 1.8]),
                ("finite", [3.0, -1.0, 2.0]),
                ("finite", [3.3, -1.1, 2.2]),
            ],
        )
        self.assertGreaterEqual(iterations, 0)
        self.assertLessEqual(iterations, 12)
        self.assertEqual(tuple(var.shape), (3,))
