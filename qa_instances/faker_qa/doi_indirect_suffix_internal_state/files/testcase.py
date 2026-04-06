from faker import Faker


class TestDoiIndirectSuffixInternalStateQA:
    def test_doi_indirect_suffix_internal_state_case(self):
        """
        Burns the shared generator via `ean13`, `word`, and `random_digit`, then calls
        `doi()` where `suffix = bothify('?#?#?##').lower()` is assembled before the
        final f-string return.
        """
        fake = Faker()
        fake.seed_instance(135792468)
        fake.ean13()
        fake.word()
        fake.random_digit()
        fake.doi()


if __name__ == "__main__":
    t = TestDoiIndirectSuffixInternalStateQA()
    t.test_doi_indirect_suffix_internal_state_case()
