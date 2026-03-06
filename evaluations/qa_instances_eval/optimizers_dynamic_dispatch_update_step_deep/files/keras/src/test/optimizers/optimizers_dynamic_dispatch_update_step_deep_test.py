import numpy as np

from keras.src import backend
from keras.src import testing
from keras.src.optimizers.adam import Adam
from keras.src.optimizers.loss_scale_optimizer import LossScaleOptimizer


class OptimizersDynamicDispatchUpdateStepDeepQATest(testing.TestCase):
    def test_concrete_update_step_dispatched_from_base_backend_update_step(self):
        inner_optimizer = Adam(
            learning_rate=0.01,
            beta_1=0.8,
            beta_2=0.95,
            amsgrad=True,
            clipnorm=0.7,
        )
        optimizer = LossScaleOptimizer(
            inner_optimizer=inner_optimizer,
            initial_scale=128.0,
            dynamic_growth_steps=2,
        )

        variables = [
            backend.Variable(np.array([1.0 + 0.2 * i, -0.5 - 0.1 * i], dtype="float32"), name=f"dd_var_{i}")
            for i in range(3)
        ]
        finite_grads = [
            np.array([0.3 + 0.05 * i, -0.2 - 0.03 * i], dtype="float32")
            for i in range(3)
        ]
        nonfinite_grads = [
            np.array([np.nan, 0.1 + 0.01 * i], dtype="float32")
            for i in range(3)
        ]

        optimizer.apply(finite_grads, variables)
        optimizer.apply(nonfinite_grads, variables)

        for var in variables:
            self.assertEqual(tuple(var.shape), (2,))
