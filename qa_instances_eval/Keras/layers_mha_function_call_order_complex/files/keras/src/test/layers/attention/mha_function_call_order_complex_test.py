import numpy as np

from keras.src import backend
from keras.src import testing
from keras.src.layers.attention.multi_head_attention import MultiHeadAttention


class MultiHeadAttentionFunctionCallOrderComplexQATest(testing.TestCase):
    def test_mha_function_call_order_with_masks_causal_and_dropout(self):
        query = np.array(
            [[[0.2, -0.1, 0.4, 0.0], [0.0, 0.3, -0.5, 0.2], [0.7, -0.2, 0.1, -0.4]]],
            dtype="float32",
        )
        value = np.array(
            [
                [
                    [0.5, -0.1, 0.2, 0.0],
                    [0.0, 0.4, -0.2, 0.1],
                    [0.3, 0.2, -0.6, 0.8],
                    [-0.4, 0.1, 0.5, -0.3],
                ]
            ],
            dtype="float32",
        )
        key = np.array(
            [
                [
                    [0.1, 0.2, -0.1, 0.3],
                    [0.0, -0.3, 0.4, 0.2],
                    [0.5, 0.1, -0.2, -0.4],
                    [-0.2, 0.6, 0.0, 0.1],
                ]
            ],
            dtype="float32",
        )

        query_mask = np.array([[True, True, False]], dtype="bool")
        value_mask = np.array([[True, False, True, True]], dtype="bool")
        key_mask = np.array([[True, True, False, True]], dtype="bool")
        attention_mask = np.array(
            [[[True, True, False, True], [True, False, False, True], [True, True, True, False]]],
            dtype="bool",
        )

        layer = MultiHeadAttention(
            num_heads=2,
            key_dim=2,
            value_dim=2,
            dropout=0.25,
            use_bias=True,
            seed=17,
        )
        backend.set_keras_mask(query, query_mask)

        attention_output, attention_scores = layer(
            query=query,
            value=value,
            key=key,
            value_mask=value_mask,
            key_mask=key_mask,
            attention_mask=attention_mask,
            return_attention_scores=True,
            training=True,
            use_causal_mask=True,
        )

        self.assertEqual(tuple(np.array(attention_output).shape), (1, 3, 4))
