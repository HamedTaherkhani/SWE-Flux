from faker import Faker


class TestFakerChainedPystructPydictParseMaxCallDepthQA:
    def test_faker_chained_pystruct_pydict_parse_max_call_depth_case(self):
        """
        Single test run chains three API surfaces that fan out across providers:

        1. `pystruct` with `dict` / `list` in `value_types` builds nested structures;
           each leaf uses `_random_type` → `generator.format`, pulling other providers.

        2. `pydict` pairs `words(..., unique=True)` with `_pyiterable` / `_random_type`.

        3. `parse` walks `{{ token }}` / `{{ token:group }}` and calls `format` per token.

        Together they interleave recursion-like nesting with cross-provider dispatch,
        producing a deep faker-local call stack.
        """
        Faker.seed(13579)
        fake = Faker()
        fake.set_arguments("n", {"min_value": 1, "max_value": 3})
        fake.pystruct(count=4, value_types=(str, dict, list, int))
        fake.pydict(
            nb_elements=5,
            variable_nb_elements=False,
            value_types=(str, float),
        )
        fake.parse("{{ pyint:n }} {{ name }} {{ hex_color }}")


if __name__ == "__main__":
    t = TestFakerChainedPystructPydictParseMaxCallDepthQA()
    t.test_faker_chained_pystruct_pydict_parse_max_call_depth_case()
