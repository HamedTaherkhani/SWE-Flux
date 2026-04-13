import pytest
from faker import Faker
from faker.providers.date_time import ParseError


class TestDateTimeProviderParseIncompatibleEndDatetimeUncaughtQA:
    def test_date_time_provider_parse_incompatible_end_datetime_uncaught_case(self):
        """
        Long date_time path (decade window, past range) then date_time_between with a
        dict end_date, which _parse_date_time rejects (lines 2053–2066).
        """
        fake = Faker()
        fake.seed_instance(1729)
        fake.date_time_this_decade(before_now=True, after_now=False)
        fake.past_datetime("-10d")
        with pytest.raises(ParseError) as exc_info:
            fake.date_time_between(
                start_date="-2h",
                end_date={"tz": "invalid", "nested": [1, 2, 3]},
            )
        print(f"EXCEPTION {type(exc_info.value).__name__}: {exc_info.value!r}")


if __name__ == "__main__":
    t = TestDateTimeProviderParseIncompatibleEndDatetimeUncaughtQA()
    t.test_date_time_provider_parse_incompatible_end_datetime_uncaught_case()
