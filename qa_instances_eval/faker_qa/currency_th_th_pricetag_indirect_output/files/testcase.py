from faker import Faker


class TestCurrencyThThPricetagIndirectOutputQA:
    def test_currency_th_th_pricetag_indirect_output_case(self):
        """
        `th_TH` inherits the base `currency.Provider.pricetag` (ISO code + NBSP + numerified
        price format). Prior calls draw from `cryptocurrencies` and fiat `currency()` paths
        so the PRNG state at `pricetag` is non-obvious.
        """
        fake = Faker("th_TH")
        fake.seed_instance(314159)
        fake.cryptocurrency()
        fake.cryptocurrency_name()
        fake.currency_name()
        fake.currency_symbol()
        fake.pricetag()


if __name__ == "__main__":
    t = TestCurrencyThThPricetagIndirectOutputQA()
    t.test_currency_th_th_pricetag_indirect_output_case()
