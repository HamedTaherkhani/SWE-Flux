from faker import Faker


class TestPhoneNumberEnPhCreatePatternLenShapeQA:
    def test_phone_number_en_ph_create_pattern_len_shape_case(self):
        """
        Indirectly exercises `faker.providers.phone_number.en_PH.Provider._create_phone_number`
        through multiple public helpers that pass different `formats` tuples (mobile, carrier-specific
        mobile, and several landline buckets), advancing the shared RNG between each call.
        """
        fake = Faker("en_PH")
        fake.seed_instance(1337)
        fake.mobile_number()
        fake.globe_mobile_number()
        fake.sun_mobile_number()
        fake.smart_mobile_number()
        fake.pldt_area2_landline_number()
        fake.misc_area2_landline_number()
        fake.non_area2_landline_number()


if __name__ == "__main__":
    t = TestPhoneNumberEnPhCreatePatternLenShapeQA()
    t.test_phone_number_en_ph_create_pattern_len_shape_case()
