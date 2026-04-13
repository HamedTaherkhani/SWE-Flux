from faker import Faker


class TestPythonProviderPydictIndirectRandomTypeSeqQA:
    def test_python_provider_pydict_indirect_random_type_seq_case(self):
        """
        Indirect path: pystruct first consumes the seeded PRNG through many
        `_random_type` calls and nested `pystruct` dict/tuple wiring, then
        `pydict` pairs `words(..., unique=True)` with `_pyiterable` which calls
        `_random_type` for each dictionary value under a merged type signature.
        """
        fake = Faker()
        fake.seed_instance(424242)
        fake.pystruct(
            count=3,
            value_types=(str, int, float),
        )
        fake.pydict(
            nb_elements=4,
            variable_nb_elements=True,
            value_types=(int, str),
            allowed_types=(float,),
        )


if __name__ == "__main__":
    t = TestPythonProviderPydictIndirectRandomTypeSeqQA()
    t.test_python_provider_pydict_indirect_random_type_seq_case()
