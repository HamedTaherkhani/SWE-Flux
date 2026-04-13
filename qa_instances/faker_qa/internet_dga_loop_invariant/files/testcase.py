from __future__ import annotations

import pytest

from faker import Faker


# Each entry is (seed, length, year, month, day, tld).
# None means "use the random default" for that parameter.
# Positive lengths: range(length) iterates `length` times, one chr() append
#   per step, so len(domain) == length at line 361 — invariant holds.
# Negative lengths: -N is truthy so `length = -N or random` stays -N;
#   range(-N) is empty, domain remains "", and len("") != -N — invariant breaks.
CASES = [
    # seed    length  year   month  day    tld
    (42,      10,     None,  None,  None,  None),   # original seed 1
    (3333,    10,     None,  None,  None,  None),   # original seed 2
    (9999,    10,     2024,  10,    15,    None),   # original seed 3 + explicit date
    (100,      5,     None,  None,  None,  None),   # short domain
    (200,     63,     None,  None,  None,  None),   # max-range length
    (300,      2,     None,  None,  None,  None),   # min-range length
    (400,     20,     2024,  1,     1,     None),   # explicit date, positive length
    (500,     15,     None,  None,  None,  "com"),  # explicit tld
    (600,     30,     None,  None,  None,  "org"),  # explicit tld, longer domain
    (700,     12,     2023,  6,     15,    None),   # explicit date
    (800,      1,     None,  None,  None,  None),   # single-character domain
    (900,     50,     2024,  3,     15,    "net"),  # all explicit params, positive
    (1000,    -1,     None,  None,  None,  None),   # negative: range(-1) empty → "" ≠ -1
    (1100,    -5,     None,  None,  None,  None),   # negative: range(-5) empty → "" ≠ -5
    (1200,   -10,     None,  None,  None,  None),   # negative: range(-10) empty → "" ≠ -10
]


class TestInternetDgaLoopInvariantQA:
    @pytest.mark.parametrize("seed,length,year,month,day,tld", CASES)
    def test_dga_loop_invariant_case(
        self, seed, length, year, month, day, tld
    ):
        """
        Seed the Faker PRNG, construct a default-locale Faker, then call
        dga() with the given parameter combination.  Inside Provider.dga,
        `length` is resolved on line 353 (`length = length or random_int(...)`):
        positive integers and negative integers are both truthy and pass through
        unchanged, while None is falsy and replaced by a random positive value.
        The loop `for _ in range(length)` (line 355) appends exactly one
        character per iteration via `domain += chr(...)` (line 359).
        At line 361 (`return domain + "." + tld`) the local variables `domain`
        and `length` are in scope; the relationship `len(domain) == length`
        holds when length >= 0 but breaks when length < 0 (range(negative) is
        empty so domain stays "" while length remains negative).
        """
        Faker.seed(seed)
        fake = Faker()
        fake.dga(length=length, year=year, month=month, day=day, tld=tld)


if __name__ == "__main__":
    t = TestInternetDgaLoopInvariantQA()
    for args in CASES:
        t.test_dga_loop_invariant_case(*args)
