import numpy as np

from keras.src import layers
from keras.src import testing
from keras.src.backend.config import disable_flash_attention


class MultiHeadAttentionHardTest(testing.TestCase):
    def test_cross_attention_with_manual_reference(self):
        disable_flash_attention()

        layer = layers.MultiHeadAttention(
            num_heads=2,
            key_dim=2,
            value_dim=2,
            use_bias=False,
            dropout=0.0,
            output_shape=3,
        )

        query = np.array(
            [
                [
                    [0.5, -1.0, 0.0, 2.0],
                    [1.0, 0.5, -0.5, -1.5],
                    [-0.25, 1.5, 0.75, 0.0],
                ]
            ],
            dtype="float32",
        )
        value = np.array(
            [
                [
                    [1.0, 0.0, -1.0, 0.5],
                    [-0.5, 1.0, 0.5, -1.0],
                    [0.25, -0.75, 1.25, 0.0],
                    [1.5, 0.5, -0.25, -0.5],
                ]
            ],
            dtype="float32",
        )
        key = np.array(
            [
                [
                    [0.0, 1.0, -0.5, 1.0],
                    [1.0, -1.0, 0.25, 0.0],
                    [-0.5, 0.5, 1.0, -1.0],
                    [0.75, 0.25, -1.25, 0.5],
                ]
            ],
            dtype="float32",
        )
        attention_mask = np.array(
            [
                [
                    [True, True, False, True],
                    [False, True, True, False],
                    [True, False, True, True],
                ]
            ]
        )

        layer.build(query.shape, value.shape, key.shape)

        query_kernel = np.array(
            [
                [[0.1, -0.3], [0.2, 0.4]],
                [[-0.5, 0.6], [0.3, -0.2]],
                [[0.7, 0.0], [-0.1, 0.5]],
                [[0.25, -0.75], [0.6, 0.15]],
            ],
            dtype="float32",
        )
        key_kernel = np.array(
            [
                [[-0.2, 0.1], [0.5, -0.4]],
                [[0.35, -0.6], [0.2, 0.3]],
                [[-0.45, 0.25], [0.1, -0.2]],
                [[0.8, 0.05], [-0.35, 0.45]],
            ],
            dtype="float32",
        )
        value_kernel = np.array(
            [
                [[0.3, -0.1], [0.5, 0.2]],
                [[-0.25, 0.4], [0.15, -0.35]],
                [[0.6, 0.05], [-0.45, 0.55]],
                [[-0.1, 0.7], [0.25, -0.05]],
            ],
            dtype="float32",
        )
        output_kernel = np.array(
            [
                [[0.5, -0.2, 0.1], [0.0, 0.4, -0.3]],
                [[-0.35, 0.25, 0.45], [0.2, -0.1, 0.6]],
            ],
            dtype="float32",
        )
        layer.set_weights([query_kernel, key_kernel, value_kernel, output_kernel])

        outputs = layer(
            query=query,
            value=value,
            key=key,
            attention_mask=attention_mask,
            training=False,
        )
        outputs_np = np.array(outputs)
