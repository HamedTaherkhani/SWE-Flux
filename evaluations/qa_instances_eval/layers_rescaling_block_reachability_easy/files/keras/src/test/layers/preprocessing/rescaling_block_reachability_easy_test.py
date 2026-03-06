import numpy as np

from keras.src import backend
from keras.src import testing
from keras.src.layers.preprocessing.rescaling import Rescaling


class RescalingBlockReachabilityEasyQATest(testing.TestCase):
    def test_channels_first_scale_reshape_block_reachability(self):
        original_data_format = backend.image_data_format()
        try:
            backend.set_image_data_format("channels_first")
            layer = Rescaling(
                scale=np.array([0.5, 1.0, 1.5], dtype="float32"),
                offset=0.25,
            )
            x = np.array(
                [
                    [
                        [[1.0, 2.0], [3.0, 4.0]],
                        [[0.0, 1.0], [2.0, 3.0]],
                        [[2.0, 0.0], [1.0, 3.0]],
                    ]
                ],
                dtype="float32",
            )
            y = layer(x)
        finally:
            backend.set_image_data_format(original_data_format)

        self.assertEqual(tuple(np.array(y).shape), (1, 3, 2, 2))
