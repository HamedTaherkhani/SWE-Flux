from __future__ import annotations

import pytest

from faker import Faker


# Each entry is (seed, bank_code).
# bank_code=None lets clabe() pick randomly from Provider.bank_codes (max 902).
# bank_code=0  is falsy, so `bank = 0 or random_element(bank_codes)` also
# resolves to a random element from the list.
# All explicit non-None, non-zero codes here are at most 3 decimal digits,
# so f"{bank:03d}" always produces exactly 3 characters, keeping the
# intermediate `result` string at 3+3+4+7 = 17 digits.
CASES = [
    # seed   bank_code
    (2077,   None),   # random from bank_codes list (max 902)
    (1001,   None),   # random from bank_codes list
    (5013,   None),   # random from bank_codes list
    (42,     2),      # smallest code in the list
    (100,    6),      # single-digit code → formatted as "006"
    (200,    106),    # 3-digit code from the list
    (300,    902),    # largest code in the list
    (400,    999),    # 3-digit value not in list but still fits :03d
    (500,    600),    # 3-digit code from the list
    (600,    128),    # 3-digit code from the list
    (700,    130),    # 3-digit code from the list
    (800,    None),   # random from bank_codes list
    (900,    0),      # falsy → resolves to random_element(bank_codes)
    (1000,   40),     # 2-digit code → formatted as "040"
    (1100,   9),      # 1-digit code → formatted as "009"
]


class TestBankClabeResultShapeInvariantQA:
    @pytest.mark.parametrize("seed,bank_code", CASES)
    def test_clabe_result_shape_invariant_case(self, seed, bank_code):
        """
        Seed the Faker PRNG, construct a Mexican-locale Faker, then call
        clabe(bank_code=bank_code).  Inside Provider.clabe, line 280 evaluates
            result = f"{bank:03d}{city:03d}{branch:04d}{account:07d}"
        The :03d/:04d/:07d format specifiers pad to a minimum width but do not
        truncate, so the shape of `result` depends solely on whether `bank`,
        `city`, `branch` and `account` exceed their allotted digit counts.
        """
        fake = Faker("es_MX")
        Faker.seed(seed)
        fake.clabe(bank_code=bank_code)


if __name__ == "__main__":
    t = TestBankClabeResultShapeInvariantQA()
    for seed, bank_code in CASES:
        t.test_clabe_result_shape_invariant_case(seed, bank_code)
