from sympy.functions.combinatorial.numbers import nC


class TestFunctionsNcIndirectAopWasStateQA:
    def test_functions_nc_indirect_aop_was_state_case(self):
        bag = "aaaabbbbccccddddeee"
        k = 7

        count = nC(bag, k)

        assert isinstance(count, int)
        assert count > 0
