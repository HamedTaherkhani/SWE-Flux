import numpy as np

from keras.src import backend
from keras.src import ops
from keras.src import optimizers
from keras.src import testing


class OptimizersTensorShapeStateQATest(testing.TestCase):
    def test_grads_tensor_shape_after_clip_call(self):
        variable = backend.Variable(
            np.zeros((2, 3), dtype="float32"),
            dtype="float32",
            trainable=True,
            name="qa_shape_var",
        )
        optimizer = optimizers.SGD(learning_rate=0.5, clipvalue=0.2)
        grads = [
            ops.convert_to_tensor(
                np.array([[1.2, -0.5, 0.1], [0.7, -1.1, 2.0]], dtype="float32")
            )
        ]

        optimizer.apply(grads, [variable])
        self.assertTrue(float(ops.sum(ops.abs(variable))) > 0.0)
