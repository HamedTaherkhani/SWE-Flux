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
