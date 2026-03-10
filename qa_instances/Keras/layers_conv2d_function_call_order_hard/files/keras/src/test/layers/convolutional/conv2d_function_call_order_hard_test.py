import numpy as np

from keras.src import testing
from keras.src.layers.convolutional.conv2d import Conv2D


class Conv2DFunctionCallOrderHardQATest(testing.TestCase):
    def test_conv2d_function_call_order_grouped_channels_first_bias_activation(self):
        x = np.array(
            [
                [
                    [
                        [0.1, 0.2, 0.3, 0.4, 0.1, 0.0],
                        [0.0, 0.1, 0.2, 0.3, 0.4, 0.2],
                        [0.3, 0.2, 0.1, 0.0, 0.1, 0.3],
                        [0.2, 0.4, 0.6, 0.8, 0.2, 0.1],
                        [0.1, 0.3, 0.5, 0.7, 0.3, 0.0],
                        [0.0, 0.1, 0.0, 0.1, 0.0, 0.1],
                    ],
                    [
                        [0.2, 0.1, 0.0, 0.1, 0.2, 0.3],
                        [0.1, 0.0, 0.1, 0.2, 0.3, 0.4],
                        [0.0, 0.1, 0.2, 0.3, 0.2, 0.1],
                        [0.3, 0.4, 0.5, 0.6, 0.5, 0.4],
                        [0.2, 0.3, 0.4, 0.5, 0.4, 0.3],
                        [0.1, 0.2, 0.1, 0.2, 0.1, 0.2],
                    ],
                    [
                        [0.4, 0.3, 0.2, 0.1, 0.0, 0.1],
                        [0.3, 0.2, 0.1, 0.0, 0.1, 0.2],
                        [0.2, 0.1, 0.0, 0.1, 0.2, 0.3],
                        [0.5, 0.6, 0.7, 0.8, 0.7, 0.6],
                        [0.4, 0.5, 0.6, 0.7, 0.6, 0.5],
                        [0.3, 0.4, 0.3, 0.4, 0.3, 0.4],
                    ],
                    [
                        [0.5, 0.4, 0.3, 0.2, 0.1, 0.0],
                        [0.4, 0.3, 0.2, 0.1, 0.0, 0.1],
                        [0.3, 0.2, 0.1, 0.0, 0.1, 0.2],
                        [0.6, 0.7, 0.8, 0.9, 0.8, 0.7],
                        [0.5, 0.6, 0.7, 0.8, 0.7, 0.6],
                        [0.4, 0.5, 0.4, 0.5, 0.4, 0.5],
                    ],
                ]
            ],
            dtype="float32",
        )

        layer = Conv2D(
            filters=4,
            kernel_size=(3, 3),
            strides=(1, 1),
            padding="same",
            data_format="channels_first",
            dilation_rate=(1, 1),
            groups=2,
            activation="relu",
            use_bias=True,
        )
        y = layer(x)
        self.assertEqual(tuple(np.array(y).shape), (1, 4, 6, 6))
