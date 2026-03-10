from keras.src import testing
from keras.src.optimizers.sgd import SGD


class ProbeVariable:
    def __init__(self, path):
        self.path = path
        self.name = path.replace("/", "_")


class OptimizersGradientFilterStateProfileThetaQATest(testing.TestCase):
    def test_missing_grad_paths_before_empty_grad_exception(self):
        optimizer = SGD(
            learning_rate=0.031,
            momentum=0.2,
            nesterov=True,
            weight_decay=1e-4,
        )
        variables = [
            ProbeVariable("encoder/block_0/attn/query_kernel"),
            ProbeVariable("encoder/block_0/attn/query_bias"),
            ProbeVariable("encoder/block_1/mlp/output_kernel"),
            ProbeVariable("head/projection/kernel"),
        ]
        grads = [None, None, None, None]

        with self.assertRaisesRegex(ValueError, "No gradients provided"):
            optimizer._filter_empty_gradients(grads, variables)
