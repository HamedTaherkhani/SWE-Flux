import pytest
from faker import Faker


class TestPythonProviderPyfloatIncompatibleCompareUncaughtQA:
    def test_python_provider_pyfloat_incompatible_compare_uncaught_case(self):
        """
        Exercises a long python-provider path (pylist -> _pyiterable -> _random_type
        -> generator.format) before hitting pyfloat with incompatible min/max bounds.
        """
        fake = Faker()
        fake.seed_instance(271828)
        fake.pylist(
            nb_elements=14,
            variable_nb_elements=True,
            value_types=("str", "int", "float", "decimal", "tuple"),
            allowed_types=("date_time",),
        )
        fake.pyset(nb_elements=3, variable_nb_elements=False, value_types=("str",))
        with pytest.raises(TypeError) as exc_info:
            fake.pyfloat(min_value=[0, 1], max_value=100)
        print(f"EXCEPTION {type(exc_info.value).__name__}: {exc_info.value!r}")


if __name__ == "__main__":
    t = TestPythonProviderPyfloatIncompatibleCompareUncaughtQA()
    t.test_python_provider_pyfloat_incompatible_compare_uncaught_case()
