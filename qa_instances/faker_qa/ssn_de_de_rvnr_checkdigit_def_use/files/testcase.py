import pytest
from faker import Faker

class TestSsnDeDeRvnrCheckdigitDefUseQA:
    def test_rvnr_checkdigit_def_use_case(self):
        # Use de_DE locale and deterministic seed
        fake = Faker('de_DE')
        fake.seed_instance(42)
        
        # Invoke rvnr() which calls __get_rvnr_checkdigit
        res = fake.rvnr()
        
        # Basic assertion
        assert len(res) > 0
        assert type(res) is str
