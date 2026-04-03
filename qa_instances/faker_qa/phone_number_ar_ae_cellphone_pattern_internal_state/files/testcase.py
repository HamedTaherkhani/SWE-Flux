from faker import Faker


class TestPhoneNumberArAeCellphonePatternInternalStateQA:
    def test_phone_number_ar_ae_cellphone_pattern_internal_state_case(self):
        """
        Chains `ar_AE` helpers so the shared RNG advances through a large combined
        `formats` pool (`phone_number`) before alternating cellphone/telephone paths,
        then asks about the internal `pattern` local inside `cellphone_number`.
        """
        fake = Faker("ar_AE")
        fake.seed_instance(2026)
        fake.phone_number()
        fake.cellphone_number()
        fake.telephone_number()
        fake.cellphone_number()


if __name__ == "__main__":
    t = TestPhoneNumberArAeCellphonePatternInternalStateQA()
    t.test_phone_number_ar_ae_cellphone_pattern_internal_state_case()
