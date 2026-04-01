import unittest
from faker import Faker

class TestBarcodeEanDefUseQA(unittest.TestCase):
    def test_ean_def_use_case(self):
        fake = Faker()
        fake.seed_instance(42)
        # Using length=8 and prefixes to trigger both branches in _ean
        result = fake.ean(length=8, prefixes=("12",))
        print(f"Result: {result}")
        # For seed 42, length 8, prefix 12, the result should be deterministic
        self.assertEqual(len(result), 8)
        self.assertTrue(result.startswith("12"))

if __name__ == "__main__":
    unittest.main()
