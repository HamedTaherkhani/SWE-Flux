from sympy.ntheory.factor_ import primefactors


class TestNTheoryPrimefactorsExecutionPathLinesQA:
    def test_ntheory_primefactors_execution_path_lines_case(self):
        seed = (2**8) * (3**5) * (5**2) * (7**2) * 11 * 13 * 17
        value = seed * 99991

        primes = primefactors(
            value,
            limit=100500,
            use_rho=False,
            use_pm1=False,
            use_ecm=False,
        )

        assert len(primes) >= 8
        assert all(value % p == 0 for p in primes)
