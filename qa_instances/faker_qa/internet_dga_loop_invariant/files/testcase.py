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
