from faker import Faker


class TestMiscProviderPasswordLinePathDeterminismQA:
    def test_misc_provider_password_line_path_determinism_case(self):
        """
        Misc `password` walks a long, branchy path: per-flag `required_tokens`
        and `choices` assembly, assertion on length vs. required categories, then a
        rejection-sampling loop with `random.sample` / `shuffle` until charset
        constraints pass. With a fixed `Faker.seed`, the shared module-level PRNG
        is reset identically at the start of each pytest process, so line-level
        execution inside `Provider.password` should repeat across runs.
        """
        Faker.seed(20260403)
        fake = Faker()
        fake.password(
            length=24,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True,
        )


if __name__ == "__main__":
    t = TestMiscProviderPasswordLinePathDeterminismQA()
    t.test_misc_provider_password_line_path_determinism_case()
