import numpy as np

from keras.src import backend
from keras.src import testing
from keras.src.optimizers.sgd import SGD


class OptimizersCallFrequencySlotCreationBranchQATest(testing.TestCase):
    def test_add_variable_from_reference_frequency_in_build_branch(self):
        optimizer = SGD(
            learning_rate=0.1,
            momentum=0.5,
            nesterov=True,
            clipnorm=0.75,
        )

        variables = [
            backend.Variable(np.array([1.0, -1.0], dtype="float32"), name=f"v{i}")
            for i in range(7)
        ]
        grads = [
            np.array([2.5 + 0.1 * i, -1.7 - 0.05 * i], dtype="float32")
            for i in range(7)
        ]

        optimizer.apply(grads, variables)

        for var in variables:
            self.assertEqual(tuple(var.shape), (2,))
