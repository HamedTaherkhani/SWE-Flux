import json
import os

import numpy as np

from keras.src import testing
from keras.src.layers.regularization.dropout import Dropout


class DropoutRepeatProfileBetaQATest(testing.TestCase):
    def test_repeated_output_profile(self):
        run_index = int(os.environ.get("QA_RUN_INDEX", "1"))
        inputs = np.array(
            [
                [0.25, -0.75, 1.5, -2.0, 2.75, -3.25, 4.5, -5.0, 5.5, -6.25, 7.0, -7.75],
                [0.5, -1.25, 2.25, -2.5, 3.5, -4.75, 5.25, -6.0, 6.75, -7.5, 8.25, -9.0],
                [0.75, -1.5, 2.75, -3.0, 4.25, -5.5, 6.0, -6.75, 7.5, -8.25, 9.0, -9.75],
                [1.0, -1.75, 3.25, -3.5, 4.75, -6.0, 6.5, -7.25, 8.0, -8.75, 9.5, -10.25],
            ],
            dtype="float32",
        )
        layer = Dropout(rate=0.35)
        output_tensor = np.array(layer(inputs, training=True))
        output_tensor = np.round(output_tensor, 6)

        payload = {
            "run_index": run_index,
            "output_tensor": output_tensor.tolist(),
            "output_sum": float(np.round(np.sum(output_tensor), 6)),
        }
        print("QA_PAYLOAD:" + json.dumps(payload, separators=(",", ":")))

        self.assertEqual(tuple(output_tensor.shape), (4, 12))
