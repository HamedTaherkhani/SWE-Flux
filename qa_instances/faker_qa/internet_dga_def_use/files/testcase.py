import unittest
from faker import Faker

class TestInternetDgaDefUseQA(unittest.TestCase):
    def test_dga_def_use_case(self):
        fake = Faker()
        fake.seed_instance(42)
        # Using fixed parameters to ensure deterministic loop and bitwise logic
        # length=3 ensures 3 iterations of the mutation logic
        result = fake.dga(year=2023, month=10, day=27, length=3)
        print(f"Result: {result}")
        # For seed 42 and fixed inputs, result is deterministic.
        # Length 3 + TLD should be like 'abc.com'
        self.assertGreater(len(result), 3)
        self.assertIn(".", result)

if __name__ == "__main__":
    unittest.main()
