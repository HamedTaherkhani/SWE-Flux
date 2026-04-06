import pytest
from faker import Faker

class TestLoremTextDefUseQA:
    def test_lorem_text_def_use_case(self):
        # We use a deterministic seed and the en_US locale
        fake = Faker('en_US')
        fake.seed_instance(42)
        
        # We invoke the text method with a short limit to trigger the `< 25` character logic branch
        # which evaluates the `while size < max_nb_chars:` generation loop and
        # appends words iteratively.
        res = fake.text(max_nb_chars=15)

        # Basic assertion to ensure execution wasn't skipped
        assert len(res) > 0
        assert type(res) is str
