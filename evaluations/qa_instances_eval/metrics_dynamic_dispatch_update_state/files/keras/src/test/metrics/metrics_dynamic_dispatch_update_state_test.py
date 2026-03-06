import numpy as np

from keras.src import testing
from keras.src.metrics.accuracy_metrics import BinaryAccuracy


class MetricsDynamicDispatchUpdateStateQATest(testing.TestCase):
    def test_concrete_update_state_dispatched_from_metric_call(self):
        metric = BinaryAccuracy(name="dispatch_binary_acc", threshold=0.35)

        y_true = np.array([1, 0, 1, 1, 0, 0], dtype="float32")
        y_pred = np.array([0.9, 0.7, 0.2, 0.8, 0.1, 0.4], dtype="float32")
        sample_weight = np.array([1.0, 0.5, 1.5, 1.0, 0.7, 0.3], dtype="float32")

        result = metric(y_true, y_pred, sample_weight=sample_weight)
        metric(y_true, y_pred)

        self.assertEqual(tuple(np.array(result).shape), ())
