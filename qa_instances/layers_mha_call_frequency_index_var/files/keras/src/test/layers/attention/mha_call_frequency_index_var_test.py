import numpy as np

from keras.src import testing
from keras.src.layers.attention.multi_head_attention import MultiHeadAttention


class MultiHeadAttentionCallFrequencyIndexVarQATest(testing.TestCase):
    def test_index_to_einsum_variable_call_frequency(self):
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

        layer = MultiHeadAttention(
            num_heads=4,
            key_dim=2,
            value_dim=2,
            dropout=0.2,
            use_bias=True,
            seed=19,
        )

        output, scores = layer(
            query=query,
            value=value,
            key=None,
            attention_mask=np.array(
                [[[True, True, False, True], [True, False, False, True], [True, True, True, False]]],
                dtype="bool",
            ),
            return_attention_scores=True,
            training=True,
            use_causal_mask=True,
        )

        self.assertEqual(tuple(np.array(output).shape), (1, 3, 4))
