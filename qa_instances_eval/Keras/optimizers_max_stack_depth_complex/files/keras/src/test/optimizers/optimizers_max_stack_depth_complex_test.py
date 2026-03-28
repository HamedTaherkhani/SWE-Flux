import numpy as np

from keras.src import backend
from keras.src import testing
from keras.src.optimizers.adam import Adam
from keras.src.optimizers.loss_scale_optimizer import LossScaleOptimizer


class OptimizersMaxStackDepthComplexQATest(testing.TestCase):
    def test_max_stack_depth_with_loss_scale_finite_and_nonfinite_branches(self):
        inner_optimizer = Adam(
            learning_rate=0.01,
            beta_1=0.8,
            beta_2=0.95,
            amsgrad=True,
            clipnorm=0.7,
        )
        optimizer = LossScaleOptimizer(
            inner_optimizer=inner_optimizer,
            initial_scale=256.0,
            dynamic_growth_steps=2,
        )

        variables = [
            backend.Variable(
                np.array([1.0 + 0.1 * i, -0.5 - 0.2 * i], dtype="float32"),
                name=f"cvar_{i}",
            )
            for i in range(5)
        ]

        finite_grads = [
            np.array([0.4 + 0.03 * i, -0.2 - 0.02 * i], dtype="float32")
            for i in range(5)
        ]
        nonfinite_grads = [
            np.array([np.nan, 0.1 + 0.01 * i], dtype="float32")
            for i in range(5)
        ]
        finite_grads_2 = [
            np.array([0.15 + 0.02 * i, -0.05 - 0.01 * i], dtype="float32")
            for i in range(5)
        ]

        optimizer.apply(finite_grads, variables)
        optimizer.apply(nonfinite_grads, variables)
        optimizer.apply(finite_grads_2, variables)

        for var in variables:
            self.assertEqual(tuple(var.shape), (2,))
