import pytest
from faker import Faker

class TestInternetDgaLoopInvariantQA:
    def test_dga_loop_invariant_case(self):
        fake = Faker()
        # Seed 1
        Faker.seed(42)
        fake.dga()
        # Seed 2
        Faker.seed(3333)
        fake.dga(length=10)
        # Seed 3
        Faker.seed(9999)
        fake.dga(length=10, year=2024, month=10, day=15)

    def test_dga_fixed_length_5_case(self):
        """
        `dga(length=5)` runs the loop exactly 5 times, appending one character
        per iteration. At line 361, `len(domain) == 5 == length`, so the
        relationship `len(domain) == length` holds.
        """
        fake = Faker()
        Faker.seed(100)
        fake.dga(length=5)

    def test_dga_fixed_length_63_case(self):
        """
        `dga(length=63)` is the maximum allowed random length. The loop appends
        63 characters; at line 361 `len(domain) == 63 == length`, confirming the
        invariant holds for the upper boundary.
        """
        fake = Faker()
        Faker.seed(200)
        fake.dga(length=63)

    def test_dga_fixed_length_2_case(self):
        """
        `dga(length=2)` is the minimum possible random length. The loop runs
        exactly twice; at line 361 `len(domain) == 2 == length`, confirming the
        invariant holds at the lower boundary.
        """
        fake = Faker()
        Faker.seed(300)
        fake.dga(length=2)

    def test_dga_explicit_date_length20_case(self):
        """
        All date components are explicitly provided (`year=2024, month=1, day=1`)
        along with `length=20`. The loop runs exactly 20 times; at line 361
        `len(domain) == 20 == length`, so the invariant holds.
        """
        fake = Faker()
        Faker.seed(400)
        fake.dga(year=2024, month=1, day=1, length=20)

    def test_dga_with_tld_com_case(self):
        """
        Explicit `tld='com'` with `length=15`; the tld affects only the suffix
        after the dot, not `domain`. The loop appends 15 characters; at line 361
        `len(domain) == 15 == length`, satisfying the invariant.
        """
        fake = Faker()
        Faker.seed(500)
        fake.dga(length=15, tld='com')

    def test_dga_five_random_seeds_case(self):
        """
        Five `dga()` calls each with no `length` argument. `length` becomes a
        random integer in [2, 63] per `random_int(min=2, max=63)`. In each call,
        the loop runs exactly `length` times, so `len(domain) == length` holds
        at line 361 for every evaluation.
        """
        fake = Faker()
        Faker.seed(10)
        fake.dga()
        Faker.seed(20)
        fake.dga()
        Faker.seed(30)
        fake.dga()
        Faker.seed(40)
        fake.dga()
        Faker.seed(50)
        fake.dga()

    def test_dga_mixed_lengths_case(self):
        """
        Three calls with different length sources: `dga()` (random length),
        `dga(length=10)`, and `dga(length=20)`. All use positive lengths;
        in each case the loop appends exactly `length` characters, so the
        invariant `len(domain) == length` holds at line 361 for every evaluation.
        """
        fake = Faker()
        Faker.seed(600)
        fake.dga()
        fake.dga(length=10)
        fake.dga(length=20)

    def test_dga_length_1_case(self):
        """
        `dga(length=1)` runs the loop exactly once, appending a single character
        (`chr(((year ^ month ^ day) % 25) + 97)`). At line 361, `len(domain) == 1
        == length`, so the invariant holds for this single-character domain.
        """
        fake = Faker()
        Faker.seed(700)
        fake.dga(length=1)

    def test_dga_length_50_explicit_date_case(self):
        """
        `dga(length=50, year=2023, month=6, day=15)` runs the loop 50 times with
        fixed date components. The XOR/shift operations on year/month/day update
        those locals each iteration but `domain` still grows by exactly one char
        per step; at line 361 `len(domain) == 50 == length`.
        """
        fake = Faker()
        Faker.seed(800)
        fake.dga(length=50, year=2023, month=6, day=15)

    def test_dga_negative_length_minus_one_case(self):
        """
        `dga(length=-1)`: since -1 is truthy, `length = -1 or random` = -1.
        `range(-1)` is empty, so the loop never executes and `domain` stays `""`.
        At line 361: `len("") == 0 != -1 == length`, breaking the invariant
        `len(domain) == length`.
        """
        fake = Faker()
        Faker.seed(900)
        fake.dga(length=-1)

    def test_dga_negative_length_minus_five_case(self):
        """
        `dga(length=-5)`: -5 is truthy, so `length = -5`. `range(-5)` is empty;
        `domain` remains `""`. At line 361: `len("") == 0 != -5 == length`,
        violating the `len(domain) == length` invariant.
        """
        fake = Faker()
        Faker.seed(1000)
        fake.dga(length=-5)

    def test_dga_valid_then_negative_case(self):
        """
        First call `dga(length=10)` satisfies `len(domain) == 10`. Second call
        `dga(length=-1)` gives `len(domain) == 0 != -1`. Because the invariant
        must hold for EVERY evaluation at line 361, the single negative-length
        violation makes `invariant_exists` false.
        """
        fake = Faker()
        Faker.seed(1100)
        fake.dga(length=10)
        fake.dga(length=-1)

    def test_dga_tld_org_length_30_case(self):
        """
        `dga(length=30, tld='org')`: the explicit TLD replaces the random one but
        does not affect `domain` construction. The loop runs 30 times; at line 361
        `len(domain) == 30 == length`, so the invariant holds.
        """
        fake = Faker()
        Faker.seed(1200)
        fake.dga(length=30, tld='org')

    def test_dga_all_explicit_params_case(self):
        """
        All five parameters supplied: `year=2024, month=3, day=15, tld='net',
        length=12`. No random calls are made; the loop runs exactly 12 times;
        at line 361 `len(domain) == 12 == length`, confirming the invariant.
        """
        fake = Faker()
        Faker.seed(1300)
        fake.dga(year=2024, month=3, day=15, tld='net', length=12)
