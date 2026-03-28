import json
import os

import numpy as np

from keras.src import testing
from keras.src.layers.regularization.dropout import Dropout


class DropoutRepeatProfileAlphaQATest(testing.TestCase):
    def test_repeated_output_profile(self):
        run_index = int(os.environ.get("QA_RUN_INDEX", "1"))
        inputs = np.array(
            [
                [0.5, -1.0, 2.0, -3.5, 4.0, -5.0],
                [1.5, -2.5, 3.0, -4.0, 5.5, -6.5],
            ],
            dtype="float32",
        )
        layer = Dropout(rate=0.35, noise_shape=(1, 6), seed=2718)
        output_tensor = np.array(layer(inputs, training=True))
        output_tensor = np.round(output_tensor, 6)

        payload = {
            "run_index": run_index,
            "output_tensor": output_tensor.tolist(),
            "output_sum": float(np.round(np.sum(output_tensor), 6)),
        }
        print("QA_PAYLOAD:" + json.dumps(payload, separators=(",", ":")))

        self.assertEqual(tuple(output_tensor.shape), (2, 6))
