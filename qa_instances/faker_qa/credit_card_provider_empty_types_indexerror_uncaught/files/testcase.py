import pytest
from collections import OrderedDict

from faker import Faker


class TestCreditCardProviderEmptyTypesIndexErrorUncaughtQA:
    def test_credit_card_provider_empty_types_indexerror_uncaught_case(self):
        """
        Exercise number generation, expiry, and security code, then replace the
        card-type catalog so `credit_card_provider` cannot pick a type.
        """
        fake = Faker()
        fake.seed_instance(2357)
        fake.credit_card_number()
        fake.credit_card_expire()
        fake.credit_card_security_code()
        cc_provider = fake.provider("faker.providers.credit_card")
        assert cc_provider is not None
        cc_provider.credit_card_types = OrderedDict()
        with pytest.raises(IndexError) as exc_info:
            fake.credit_card_provider()
        print(f"EXCEPTION {type(exc_info.value).__name__}: {exc_info.value!r}")


if __name__ == "__main__":
    t = TestCreditCardProviderEmptyTypesIndexErrorUncaughtQA()
    t.test_credit_card_provider_empty_types_indexerror_uncaught_case()
