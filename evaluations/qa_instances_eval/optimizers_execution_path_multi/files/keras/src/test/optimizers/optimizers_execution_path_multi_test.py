import numpy as np

from keras.src import backend
from keras.src import ops
from keras.src import optimizers
from keras.src import testing


class OptimizersExecutionPathMultiQATest(testing.TestCase):
    def test_exact_execution_path_across_optimizer_files(self):
        variable = backend.Variable(
            np.array([1.0, -1.0], dtype="float32"),
            dtype="float32",
            trainable=True,
            name="qa_path_var",
        )
        optimizer = optimizers.SGD(
            learning_rate=0.2,
            momentum=0.9,
            nesterov=True,
            clipvalue=0.5,
        )
        grads = [ops.convert_to_tensor(np.array([1.7, -0.3], dtype="float32"))]

        optimizer.apply(grads, [variable])
        self.assertEqual(tuple(variable.shape), (2,))
