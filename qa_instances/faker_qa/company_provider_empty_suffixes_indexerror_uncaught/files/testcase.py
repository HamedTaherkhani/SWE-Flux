import pytest
from faker import Faker


class TestCompanyProviderEmptySuffixesIndexErrorUncaughtQA:
    def test_company_provider_empty_suffixes_indexerror_uncaught_case(self):
        """
        Exercise `company` (format parsing) and `catch_phrase` (nested word lists), then
        clear `company_suffixes` so `company_suffix` cannot sample.
        """
        fake = Faker()
        fake.seed_instance(1618)
        fake.company()
        fake.catch_phrase()
        fake.company_suffix()
        company_provider = fake.provider("faker.providers.company")
        assert company_provider is not None
        company_provider.company_suffixes = ()
        with pytest.raises(IndexError) as exc_info:
            fake.company_suffix()
        print(f"EXCEPTION {type(exc_info.value).__name__}: {exc_info.value!r}")


if __name__ == "__main__":
    t = TestCompanyProviderEmptySuffixesIndexErrorUncaughtQA()
    t.test_company_provider_empty_suffixes_indexerror_uncaught_case()
