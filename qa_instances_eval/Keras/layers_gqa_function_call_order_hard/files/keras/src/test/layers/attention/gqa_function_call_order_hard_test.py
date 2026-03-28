import numpy as np

from keras.src import testing
from keras.src.layers.attention.grouped_query_attention import (
    GroupedQueryAttention,
)


class GroupedQueryAttentionFunctionCallOrderHardQATest(testing.TestCase):
    def test_gqa_function_call_order_with_repeats_masks_causal_dropout(self):
        query = np.array(
            [
                [
                    [0.2, -0.1, 0.4, 0.0, 0.3, -0.2],
                    [0.0, 0.3, -0.5, 0.2, -0.1, 0.6],
                    [0.7, -0.2, 0.1, -0.4, 0.5, 0.0],
                    [-0.3, 0.4, 0.2, 0.1, -0.2, 0.8],
                ]
            ],
            dtype="float32",
        )
        value = np.array(
            [
                [
                    [0.5, -0.1, 0.2, 0.0, 0.1, -0.2],
                    [0.0, 0.4, -0.2, 0.1, 0.6, -0.1],
                    [0.3, 0.2, -0.6, 0.8, -0.4, 0.2],
                    [-0.4, 0.1, 0.5, -0.3, 0.7, 0.0],
                    [0.2, -0.5, 0.3, 0.4, -0.1, 0.9],
                ]
            ],
            dtype="float32",
        )

        query_mask = np.array([[True, True, False, True]], dtype="bool")
        value_mask = np.array([[True, False, True, True, True]], dtype="bool")
        key_mask = np.array([[True, True, False, True, True]], dtype="bool")
        attention_mask = np.array(
            [
                [
                    [True, True, False, True, True],
                    [True, False, False, True, True],
                    [True, True, True, False, True],
                    [True, True, False, True, False],
                ]
            ],
            dtype="bool",
        )

        layer = GroupedQueryAttention(
            head_dim=2,
            num_query_heads=6,
            num_key_value_heads=2,
            dropout=0.3,
            use_bias=True,
            seed=31,
        )

        output, scores = layer(
            query=query,
            value=value,
            key=None,
            query_mask=query_mask,
            value_mask=value_mask,
            key_mask=key_mask,
            attention_mask=attention_mask,
            return_attention_scores=True,
            training=True,
            use_causal_mask=True,
        )

        self.assertEqual(tuple(np.array(output).shape), (1, 4, 6))
