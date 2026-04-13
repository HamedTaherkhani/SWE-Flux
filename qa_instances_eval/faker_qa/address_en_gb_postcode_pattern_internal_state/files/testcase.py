from faker import Faker


class TestAddressEnGbPostcodePatternInternalStateQA:
    def test_address_en_gb_postcode_pattern_internal_state_case(self):
        """
        `en_GB.postcode` samples a template from `postcode_formats` then expands each
        placeholder via `_postcode_sets` in a loop. Prior `city` / `street_name` calls
        advance the shared RNG before that draw.
        """
        fake = Faker("en_GB")
        fake.seed_instance(246810)
        fake.city()
        fake.street_name()
        fake.postcode()


if __name__ == "__main__":
    t = TestAddressEnGbPostcodePatternInternalStateQA()
    t.test_address_en_gb_postcode_pattern_internal_state_case()
