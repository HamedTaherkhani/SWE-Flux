import numpy as np

from keras.src import activations
from keras.src import testing


class ActivationsFunctionCallOrderQATest(testing.TestCase):
    def test_function_call_order_relu_branch_configuration(self):
        x = np.array([-1.0, 0.1, 0.4, 2.0], dtype="float32")
        y = activations.relu(
            x,
            negative_slope=0.3,
            max_value=1.5,
            threshold=0.2,
        )
        self.assertEqual(tuple(np.array(y).shape), (4,))
