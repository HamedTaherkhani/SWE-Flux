from __future__ import annotations

import pytest

from faker import Faker


# Each entry is (seed, length, special_chars, digits, upper_case, lower_case).
# Every case uses an explicit Faker.seed so the shared module-level PRNG is
# reset to the same state at the start of each pytest process, making the
# sequence of line numbers executed inside Provider.password reproducible.
CASES = [
    # seed       length  spec   dig    upper  lower
    (20260403,   24,     True,  True,  True,  True),   # original — all flags
    (20260403,   12,     True,  True,  True,  True),   # shorter length
    (20260403,   10,     True,  True,  True,  True),   # default length
    (42,         24,     True,  True,  True,  True),   # different seed
    (0,          20,     True,  True,  True,  True),   # seed zero
    (12345,      16,     True,  True,  True,  True),
    (999,        15,     True,  True,  True,  True),
    (20260403,   16,     False, True,  True,  True),   # no special_chars
    (20260403,   16,     True,  False, True,  True),   # no digits
    (20260403,    8,     False, False, True,  True),   # letters only (2 tokens)
    (20260403,    8,     False, False, False, True),   # lower only (1 token)
    (99999,      30,     True,  True,  True,  True),   # long password
    (777,        15,     True,  True,  True,  True),
    (20260403,   16,     True,  True,  False, True),   # no upper_case
    (12345678,   20,     True,  True,  True,  True),
]


class TestMiscProviderPasswordLinePathDeterminismQA:
    @pytest.mark.parametrize(
        "seed,length,special_chars,digits,upper_case,lower_case", CASES
    )
    def test_misc_provider_password_line_path_determinism_case(
        self, seed, length, special_chars, digits, upper_case, lower_case
    ):
        """
        Reset the shared PRNG with Faker.seed(seed), construct a Faker instance,
        then call password() with the given parameter combination.  The fixed
        seed ensures the same sequence of random draws — and therefore the same
        control-flow path through required_tokens assembly, the while-loop that
        picks unique indexes, and the final character substitution — on every
        independent pytest invocation.
        """
        Faker.seed(seed)
        fake = Faker()
        fake.password(
            length=length,
            special_chars=special_chars,
            digits=digits,
            upper_case=upper_case,
            lower_case=lower_case,
        )


if __name__ == "__main__":
    t = TestMiscProviderPasswordLinePathDeterminismQA()
    for args in CASES:
        t.test_misc_provider_password_line_path_determinism_case(*args)
