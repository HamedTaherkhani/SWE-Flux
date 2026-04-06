import pytest
from faker import Faker

class TestDatetimeThaiStrftimeDefUseQA:
    def test_thai_strftime_def_use_case(self):
        # We use a deterministic seed and the th_TH locale
        fake = Faker('th_TH')
        fake.seed_instance(42)
        
        # We invoke the date method with a custom format string to trigger
        # the thai_strftime loop for comprehensive path coverage
        res = fake.date(pattern="%Y-%m-%d %H:%M:%S")

        # Basic assertion to ensure execution wasn't skipped
        assert len(res) > 0
        assert type(res) is str
