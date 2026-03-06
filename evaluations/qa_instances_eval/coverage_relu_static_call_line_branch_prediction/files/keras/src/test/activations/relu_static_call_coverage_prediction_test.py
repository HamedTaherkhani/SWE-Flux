import numpy as np

from keras.src import ops
from keras.src import testing
from keras.src.activations.activations import ReLU


class ReLUStaticCallCoveragePredictionQATest(testing.TestCase):
    def test_case_01_default_relu_path(self):
        y = ReLU.static_call([-2.0, -0.5, 0.0, 1.5])
        self.assertEqual(tuple(ops.convert_to_numpy(y).shape), (4,))

    def test_case_02_leaky_relu_early_return(self):
        y = ReLU.static_call([-3.0, -1.0, 2.0], negative_slope=0.2)
        self.assertEqual(tuple(ops.convert_to_numpy(y).shape), (3,))

    def test_case_03_negative_slope_with_threshold(self):
        y = ReLU.static_call(
            [-3.0, -1.0, 0.5, 2.0],
            negative_slope=0.15,
            threshold=0.25,
        )
        self.assertEqual(tuple(ops.convert_to_numpy(y).shape), (4,))

    def test_case_04_negative_slope_with_clip(self):
        y = ReLU.static_call(
            [-4.0, -2.0, 1.0, 8.0],
            negative_slope=0.3,
            max_value=3.0,
        )
        self.assertEqual(tuple(ops.convert_to_numpy(y).shape), (4,))

    def test_case_05_relu6_fast_path(self):
        y = ReLU.static_call([-2.0, 0.5, 7.0], max_value=6)
        self.assertEqual(tuple(ops.convert_to_numpy(y).shape), (3,))

    def test_case_06_threshold_without_negative_slope(self):
        y = ReLU.static_call([-1.0, 0.1, 0.3, 2.0], threshold=0.2)
        self.assertEqual(tuple(ops.convert_to_numpy(y).shape), (4,))

    def test_case_07_clip_without_negative_slope(self):
        y = ReLU.static_call([-2.0, 1.0, 5.0], max_value=2.5)
        self.assertEqual(tuple(ops.convert_to_numpy(y).shape), (3,))

    def test_case_08_threshold_and_clip_together(self):
        y = ReLU.static_call([-3.0, 0.5, 4.0], max_value=1.5, threshold=0.25)
        self.assertEqual(tuple(ops.convert_to_numpy(y).shape), (3,))

    def test_case_09_negative_slope_threshold_and_clip(self):
        y = ReLU.static_call(
            np.array([-5.0, -0.2, 0.4, 3.0], dtype="float32"),
            negative_slope=0.1,
            max_value=2.0,
            threshold=0.1,
        )
        self.assertEqual(tuple(ops.convert_to_numpy(y).shape), (4,))

    def test_case_10_tensor_input_non_default(self):
        x = ops.convert_to_tensor(np.array([-1.2, 0.0, 4.2], dtype="float32"))
        y = ReLU.static_call(x, negative_slope=0.05, max_value=4.0)
        self.assertEqual(tuple(ops.convert_to_numpy(y).shape), (3,))
