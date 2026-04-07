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

    def test_misc_provider_password_seeded_length12_all_flags_case(self):
        """
        With `Faker.seed(20260403)` and `length=12`, all four character-category
        flags enabled; the PRNG stream is deterministic so `Provider.password`
        follows the same sequence of line numbers across independent runs.
        """
        Faker.seed(20260403)
        fake = Faker()
        fake.password(
            length=12,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True,
        )

    def test_misc_provider_password_seeded_length10_all_flags_case(self):
        """
        With `Faker.seed(20260403)` and the default `length=10`, all flags enabled;
        the fixed seed resets the PRNG identically each process so branching and the
        index-selection loop repeat the same line sequence every run.
        """
        Faker.seed(20260403)
        fake = Faker()
        fake.password(
            length=10,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True,
        )

    def test_misc_provider_password_seeded_no_special_chars_case(self):
        """
        With `Faker.seed(20260403)` and `special_chars=False`, the `choices` string
        omits `!@#$%^&*()_+` and `required_tokens` has only 3 entries; the
        deterministic PRNG ensures the same line sequence is followed every run.
        """
        Faker.seed(20260403)
        fake = Faker()
        fake.password(
            length=16,
            special_chars=False,
            digits=True,
            upper_case=True,
            lower_case=True,
        )

    def test_misc_provider_password_seeded_no_digits_case(self):
        """
        With `Faker.seed(20260403)` and `digits=False`, the digit alphabet is
        excluded from `choices` and `required_tokens` contains 3 items; the fixed
        seed makes the line execution path invariant across runs.
        """
        Faker.seed(20260403)
        fake = Faker()
        fake.password(
            length=16,
            special_chars=True,
            digits=False,
            upper_case=True,
            lower_case=True,
        )

    def test_misc_provider_password_seeded_only_lower_case_case(self):
        """
        With `Faker.seed(20260403)` and only `lower_case=True`, a single required
        token is drawn from the lowercase alphabet; the minimal one-token path is
        deterministic and repeats the same line sequence across runs.
        """
        Faker.seed(20260403)
        fake = Faker()
        fake.password(
            length=8,
            special_chars=False,
            digits=False,
            upper_case=False,
            lower_case=True,
        )

    def test_misc_provider_password_seeded_42_all_flags_case(self):
        """
        With `Faker.seed(42)` and `length=24`, all four flags enabled; a different
        fixed seed still resets the PRNG deterministically so repeated runs produce
        the same line-execution sequence inside `Provider.password`.
        """
        Faker.seed(42)
        fake = Faker()
        fake.password(
            length=24,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True,
        )

    def test_misc_provider_password_seeded_0_length20_case(self):
        """
        With `Faker.seed(0)` and `length=20`, all flags enabled; seed zero is a
        valid deterministic PRNG reset, ensuring reproducible line execution inside
        `Provider.password` across independent runs.
        """
        Faker.seed(0)
        fake = Faker()
        fake.password(
            length=20,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True,
        )

    def test_misc_provider_password_seeded_12345_length16_case(self):
        """
        With `Faker.seed(12345)` and `length=16`, all flags enabled; the controlled
        PRNG seed guarantees that the `while random_indexes` collision-avoidance
        loop runs the same number of iterations on every independent run.
        """
        Faker.seed(12345)
        fake = Faker()
        fake.password(
            length=16,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True,
        )

    def test_misc_provider_password_unseeded_length24_case(self):
        """
        Unseeded `password` with `length=24` and all flags enabled; the shared
        PRNG starts in an unpredictable OS-entropy-derived state, so the
        `while random_indexes` loop may run a different number of iterations across
        independent pytest invocations, changing the executed line sequence.
        """
        fake = Faker()
        fake.password(
            length=24,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True,
        )

    def test_misc_provider_password_unseeded_length12_case(self):
        """
        Unseeded `password` with `length=12` and all flags; without a fixed seed
        the PRNG state differs between processes, causing the collision-driven
        `while` loop count and resulting line sequence to vary across runs.
        """
        fake = Faker()
        fake.password(
            length=12,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True,
        )

    def test_misc_provider_password_seeded_no_upper_case_case(self):
        """
        With `Faker.seed(20260403)` and `upper_case=False`, the uppercase branch
        inside `Provider.password` is skipped; with 3 required tokens and a fixed
        seed, the line execution sequence is invariant across runs.
        """
        Faker.seed(20260403)
        fake = Faker()
        fake.password(
            length=16,
            special_chars=True,
            digits=True,
            upper_case=False,
            lower_case=True,
        )

    def test_misc_provider_password_seeded_99999_length30_case(self):
        """
        With `Faker.seed(99999)` and `length=30`, all flags enabled; the longer
        password reduces birthday-collision probability in the index-selection loop,
        and the deterministic seed still makes the line trace invariant.
        """
        Faker.seed(99999)
        fake = Faker()
        fake.password(
            length=30,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True,
        )

    def test_misc_provider_password_seeded_no_special_no_digits_case(self):
        """
        With `Faker.seed(20260403)`, `special_chars=False`, and `digits=False`,
        only letter categories contribute to `required_tokens` (2 items); the
        2-token seeded case follows a fixed line sequence across independent runs.
        """
        Faker.seed(20260403)
        fake = Faker()
        fake.password(
            length=8,
            special_chars=False,
            digits=False,
            upper_case=True,
            lower_case=True,
        )

    def test_misc_provider_password_seeded_777_length15_case(self):
        """
        With `Faker.seed(777)` and `length=15`, all flags enabled; the PRNG is
        reset to the same state at the start of every process, so `Provider.password`
        executes the same lines in the same order across all independent runs.
        """
        Faker.seed(777)
        fake = Faker()
        fake.password(
            length=15,
            special_chars=True,
            digits=True,
            upper_case=True,
            lower_case=True,
        )


if __name__ == "__main__":
    t = TestMiscProviderPasswordLinePathDeterminismQA()
    t.test_misc_provider_password_line_path_determinism_case()
