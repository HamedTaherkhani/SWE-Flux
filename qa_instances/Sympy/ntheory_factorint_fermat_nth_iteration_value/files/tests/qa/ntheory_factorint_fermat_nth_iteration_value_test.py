from sympy.ntheory.factor_ import primefactors


class TestNTheoryFactorintFermatNthIterationValueQA:
    def test_ntheory_factorint_fermat_nth_iteration_value_case(self):
        factors = primefactors(10000029966999901)

        assert factors == [1000003, 9999999967]
