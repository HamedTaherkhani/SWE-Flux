import numpy as np

from keras.src import backend
from keras.src import optimizers
from keras.src import testing


class OptimizersProjectExceptionDeepQATest(testing.TestCase):
    def test_exception_from_filter_empty_gradients_path(self):
        variable = backend.Variable(
            np.array([1.0, -2.0, 3.0], dtype="float32"),
            dtype="float32",
            trainable=True,
            name="qa_exc_var",
        )
        optimizer = optimizers.SGD(
            learning_rate=0.1,
            gradient_accumulation_steps=2,
        )

        # Intentionally pass only empty gradients. This fails in the project
        # code path: BaseOptimizer.apply -> _filter_empty_gradients.
        grads = [None]
        trainable_variables = [variable]

        project_exception_type = None
        project_exception_message = None
        try:
            optimizer.apply(grads, trainable_variables)
        except Exception as e:
            project_exception_type = type(e).__name__
            project_exception_message = str(e)

        self.assertIsNotNone(project_exception_type)
        self.assertTrue(len(project_exception_message) > 0)
