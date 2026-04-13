import pytest
from faker import Faker

class TestSsnZhTwChecksumDefUseQA:
    def test_ssn_zh_tw_checksum_def_use_case(self):
        # Use zh_TW locale and deterministic seed
        fake = Faker('zh_TW')
        fake.seed_instance(42)
        
        # Invoke ssn() which calls checksum()
        res = fake.ssn()
        
        # Basic assertion
        assert len(res) == 10
        assert type(res) is str
