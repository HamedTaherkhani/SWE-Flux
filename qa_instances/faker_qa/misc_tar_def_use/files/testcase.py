import unittest
from faker import Faker

class TestMiscTarDefUseQA(unittest.TestCase):
    def test_tar_def_use_case(self):
        fake = Faker()
        fake.seed_instance(42)
        # uncompressed_size=10000, num_files=4, min_file_size=1000
        # Forces a 4 iteration loop generating dummy tar contents
        result = fake.tar(uncompressed_size=10000, num_files=4, min_file_size=1000)
        print(f"Result length: {len(result)}")
        # Output should be bytes
        self.assertIsInstance(result, bytes)
        # Due to tar overhead, it will be larger than 10000
        self.assertTrue(len(result) > 10000)

if __name__ == "__main__":
    unittest.main()
