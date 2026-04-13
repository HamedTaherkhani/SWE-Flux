from faker import Faker


class TestDoiIndirectFullReturnOutputQA:
    def test_doi_indirect_full_return_output_case(self):
        """
        Advances the shared `generator` PRNG through several unrelated providers, then
        calls `doi()` where `registrant = str(randint(1000, 99999999))` (variable digit
        length) before `bothify` builds `suffix`.
        """
        fake = Faker()
        fake.seed_instance(777777)
        fake.uuid4()
        fake.password(length=12)
        fake.lexify("????")
        fake.hex_color()
        fake.doi()


if __name__ == "__main__":
    t = TestDoiIndirectFullReturnOutputQA()
    t.test_doi_indirect_full_return_output_case()
