from sympy import Array, symbols, tensorcontraction


class TestTensorTensorcontractionGetTupleIndexCallFrequencyQA:
    def test_tensor_tensorcontraction_get_tuple_index_call_frequency_case(self):
        x = symbols("x0:81")
        array4d = Array(list(x), (3, 3, 3, 3))

        contracted = tensorcontraction(array4d, (0, 2), (1, 3))

        expected = sum(array4d[i, j, i, j] for i in range(3) for j in range(3))
        assert contracted == expected
