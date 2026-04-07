import pytest
from faker import Faker

class TestBankClabeResultShapeInvariantQA:
    def test_clabe_result_shape_invariant(self):
        fake = Faker("es_MX")
        Faker.seed(2077)
        fake.clabe()
        Faker.seed(1001)
        fake.clabe()
        Faker.seed(5013)
        fake.clabe()

    def test_clabe_five_random_calls_case(self):
        """
        Five `clabe()` calls with no explicit bank_code across different seeds.
        `bank` is always drawn from `bank_codes` (max value 902), so `:03d`
        formats it as exactly 3 digits; `result` at line 280 is always 17 digits.
        """
        fake = Faker("es_MX")
        Faker.seed(10)
        fake.clabe()
        Faker.seed(20)
        fake.clabe()
        Faker.seed(30)
        fake.clabe()
        Faker.seed(40)
        fake.clabe()
        Faker.seed(50)
        fake.clabe()

    def test_clabe_bank_code_2_case(self):
        """
        Explicit `bank_code=2` (single digit) is formatted by `:03d` as `"002"`.
        The resulting `result` string is `"002" + 3-digit city + 4-digit branch +
        7-digit account` = exactly 17 characters of digits.
        """
        fake = Faker("es_MX")
        Faker.seed(100)
        fake.clabe(bank_code=2)

    def test_clabe_bank_code_106_case(self):
        """
        Explicit `bank_code=106` (a 3-digit code present in `bank_codes`).
        `:03d` formats it as `"106"` (exactly 3 chars); result at line 280 has
        3+3+4+7=17 digits, satisfying the shape invariant.
        """
        fake = Faker("es_MX")
        Faker.seed(200)
        fake.clabe(bank_code=106)

    def test_clabe_bank_code_902_max_listed_case(self):
        """
        `bank_code=902` is the largest value in the `bank_codes` tuple.
        `:03d` produces `"902"` (3 digits); the shape invariant holds because
        902 is representable within 3 decimal digits.
        """
        fake = Faker("es_MX")
        Faker.seed(300)
        fake.clabe(bank_code=902)

    def test_clabe_bank_code_999_three_digit_case(self):
        """
        `bank_code=999` is not in `bank_codes` but is still a 3-digit number.
        `:03d` formats it as `"999"` (exactly 3 chars), so `result` remains
        17 characters long and all-digit.
        """
        fake = Faker("es_MX")
        Faker.seed(400)
        fake.clabe(bank_code=999)

    def test_clabe_mixed_valid_codes_case(self):
        """
        Mix of calls: one with no bank_code (random from list), one with
        `bank_code=2`, one with `bank_code=902`. All bank codes fit in 3 digits;
        `result` at line 280 is always exactly 17 decimal digits.
        """
        fake = Faker("es_MX")
        Faker.seed(500)
        fake.clabe()
        fake.clabe(bank_code=2)
        fake.clabe(bank_code=902)

    def test_clabe_bank_code_600_case(self):
        """
        `bank_code=600` is a valid 3-digit code present in the `bank_codes` list.
        `:03d` formats it as `"600"`; the concatenated `result` is 17 chars.
        """
        fake = Faker("es_MX")
        Faker.seed(600)
        fake.clabe(bank_code=600)

    def test_clabe_ten_calls_seed_42_case(self):
        """
        Ten consecutive `clabe()` calls with seed 42 and no explicit bank_code.
        Each call randomly picks from `bank_codes` (all ≤ 902), so `result` at
        line 280 always has 17 digits, confirming the shape invariant holds.
        """
        fake = Faker("es_MX")
        Faker.seed(42)
        for _ in range(10):
            fake.clabe()

    def test_clabe_bank_code_1000_overflow_case(self):
        """
        `bank_code=1000` is a 4-digit number. Python's `:03d` format specifier
        enforces a MINIMUM width of 3, not a maximum — `f"{1000:03d}"` produces
        `"1000"` (4 chars). Consequently `result` at line 280 becomes 18 chars,
        violating the 17-character shape invariant.
        """
        fake = Faker("es_MX")
        Faker.seed(700)
        fake.clabe(bank_code=1000)

    def test_clabe_bank_code_9999_case(self):
        """
        `bank_code=9999` is a 4-digit number. `f"{9999:03d}"` = `"9999"` (4 chars),
        making `result` at line 280 an 18-character string, breaking the invariant
        that `result` is exactly 17 digits.
        """
        fake = Faker("es_MX")
        Faker.seed(800)
        fake.clabe(bank_code=9999)

    def test_clabe_bank_code_10000_case(self):
        """
        `bank_code=10000` is a 5-digit number. `f"{10000:03d}"` = `"10000"` (5
        chars), so `result` at line 280 becomes 19 characters, clearly violating
        the 17-character all-digit shape invariant.
        """
        fake = Faker("es_MX")
        Faker.seed(900)
        fake.clabe(bank_code=10000)

    def test_clabe_valid_then_overflow_case(self):
        """
        First call uses no explicit bank_code (valid, 17-char result); second
        call uses `bank_code=1000` which produces an 18-char result at line 280.
        Because the invariant must hold for EVERY evaluation, one violation is
        enough to make `invariant_exists` false.
        """
        fake = Faker("es_MX")
        Faker.seed(1000)
        fake.clabe()
        fake.clabe(bank_code=1000)

    def test_clabe_three_listed_codes_case(self):
        """
        Three consecutive calls using `bank_code=128`, `bank_code=129`, and
        `bank_code=130` — all are 3-digit codes present in `bank_codes`. Each
        call produces a 17-digit `result` at line 280.
        """
        fake = Faker("es_MX")
        Faker.seed(1100)
        fake.clabe(bank_code=128)
        fake.clabe(bank_code=129)
        fake.clabe(bank_code=130)

    def test_clabe_bank_code_zero_falsy_case(self):
        """
        `bank_code=0` is falsy in Python, so `bank = 0 or self.random_element(
        self.bank_codes)` resolves to a random element from `bank_codes` (all
        ≤ 902). The second call also uses no bank_code. Both produce 17-digit
        `result` values, so the invariant holds.
        """
        fake = Faker("es_MX")
        Faker.seed(1200)
        fake.clabe(bank_code=0)
        fake.clabe()
