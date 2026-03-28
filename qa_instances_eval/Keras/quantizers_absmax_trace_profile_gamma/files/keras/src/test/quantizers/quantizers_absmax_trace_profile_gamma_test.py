import numpy as np

from keras.src import ops
from keras.src import testing
from keras.src.quantizers import quantizers


class QuantizersAbsMaxTraceProfileGammaQATest(testing.TestCase):
    def test_single_dispatch_profile(self):
        inputs = np.array(
            [
                [0.25, -1.5, 3.0, -4.25],
                [0.5, -2.0, 1.75, -3.5],
                [1.25, -0.75, 2.5, -1.0],
            ],
            dtype="float32",
        )
        to_numpy_dispatch = ((hash("absmax-profile") ^ hash("dispatch-probe")) & 1) == 0

        outputs, scale = quantizers.abs_max_quantize(
            inputs,
            axis=1,
            value_range=(-127, 127),
            dtype="int8",
            epsilon=1e-7,
            to_numpy=to_numpy_dispatch,
        )

        outputs_np = ops.convert_to_numpy(outputs)
        scale_np = ops.convert_to_numpy(scale)

        self.assertEqual(outputs_np.shape, (3, 4))
        self.assertEqual(scale_np.shape, (3, 1))
