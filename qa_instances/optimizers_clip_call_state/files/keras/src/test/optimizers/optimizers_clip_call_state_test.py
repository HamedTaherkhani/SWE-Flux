import numpy as np

from keras.src import backend
from keras.src import ops
from keras.src import optimizers
from keras.src import testing


class OptimizersClipCallStateQATest(testing.TestCase):
    def test_grads_state_after_clip_call(self):
        variable = backend.Variable(
            np.array([0.0, 0.0, 0.0], dtype="float32"),
            dtype="float32",
            trainable=True,
            name="qa_var",
        )
        optimizer = optimizers.SGD(learning_rate=1.0, clipvalue=0.25)
        grads = [
            ops.convert_to_tensor(np.array([1.2, -0.5, 0.1], dtype="float32"))
        ]

        optimizer.apply(grads, [variable])
        self.assertTrue(float(ops.sum(variable)) != 0.0)
