import numpy as np

from keras.src import backend
from keras.src import testing
from keras.src.optimizers.sgd import SGD


class OptimizersMaxStackDepthMediumQATest(testing.TestCase):
    def test_max_stack_depth_during_sgd_apply_with_clipnorm(self):
        optimizer = SGD(
            learning_rate=0.08,
            momentum=0.6,
            nesterov=True,
            clipnorm=0.9,
        )

        variables = [
            backend.Variable(np.array([1.0 + i, -0.5 * i], dtype="float32"), name=f"mvar_{i}")
            for i in range(4)
        ]
        grads = [
            np.array([2.0 + 0.2 * i, -1.5 - 0.1 * i], dtype="float32")
            for i in range(4)
        ]

        optimizer.apply(grads, variables)

        for var in variables:
            self.assertEqual(tuple(var.shape), (2,))
