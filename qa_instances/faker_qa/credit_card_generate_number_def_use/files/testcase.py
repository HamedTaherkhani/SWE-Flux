import unittest
from faker import Faker

class TestCreditCardGenerateNumberDefUseQA(unittest.TestCase):
    def test_generate_number_def_use_case(self):
        fake = Faker()
        fake.seed_instance(42)
        # Using visa16 to ensure a 16-digit credit card number is generated
        # This will cause the while loop in _generate_number to run 7 times
        result = fake.credit_card_number(card_type="visa16")
        print(f"Result: {result}")
        # Visa prefixes start with '4', and the length should be 16
        self.assertEqual(len(result), 16)
        self.assertTrue(result.startswith("4"))

if __name__ == "__main__":
    unittest.main()
