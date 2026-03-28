from sympy.ntheory.factor_ import factorint


class TestNTheoryFactorintDefUsePairsQA:
    def test_ntheory_factorint_def_use_pairs_case(self):
        factors_a = factorint(2**16 * 3**7 * 5**3 * 7 * 11 + 1)
        factors_b = factorint(1234567891011)
        factors_c = factorint(2**10 * 3**6 * 17 * 19)

        assert isinstance(factors_a, dict)
        assert isinstance(factors_b, dict)
        assert factors_c == {2: 10, 3: 6, 17: 1, 19: 1}
