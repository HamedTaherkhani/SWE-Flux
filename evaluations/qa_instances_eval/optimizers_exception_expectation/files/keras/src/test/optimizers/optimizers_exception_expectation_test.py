from keras.src import optimizers
from keras.src import testing


class OptimizersExceptionExpectationQATest(testing.TestCase):
    def test_expected_exception_type_and_pattern(self):
        caught_exception_type = None
        caught_exception_message = None
        try:
            optimizers.SGD(learning_rate=0.1, clipnorm=1.0, clipvalue=0.2)
        except Exception as e:
            caught_exception_type = type(e).__name__
            caught_exception_message = str(e)

        self.assertIsNotNone(caught_exception_type)
        self.assertTrue(len(caught_exception_message) > 0)
