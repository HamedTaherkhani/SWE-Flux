import numpy as np

from keras.src import layers
from keras.src import testing


class DenseBasicTest(testing.TestCase):
    def test_dense_basics(self):
        self.run_layer_test(
            layers.Dense,
            init_kwargs={"units": 4},
            input_shape=(2, 3),
            expected_output_shape=(2, 4),
            expected_num_trainable_weights=2,
            expected_num_non_trainable_weights=0,
            expected_num_seed_generators=0,
            expected_num_losses=0,
            supports_masking=True,
        )

    def test_dense_forward_pass(self):
        layer = layers.Dense(units=2, use_bias=False)
        layer.build((None, 2))
        layer.set_weights([np.array([[1.0, -2.0], [3.0, -4.0]])])
        outputs = layer(np.array([[-1.0, 2.0]]))
        outputs_np = np.array(outputs)
        self.assertEqual(outputs_np.shape, (1, 2))
