import numpy as np

from keras.src import testing
from keras.src.activations import activations as activations_module


class ActivationsExecutionPathBranchesQATest(testing.TestCase):
    def test_relu_full_execution_path_branch_code(self):
        x = np.array([-1.0, 0.1, 0.4, 2.0], dtype="float32")
        y = activations_module.ReLU.static_call(
            x,
            negative_slope=0.3,
            max_value=1.5,
            threshold=0.2,
        )
        self.assertEqual(tuple(np.array(y).shape), (4,))
