from faker import Faker


class TestGeneratorParseFormatCallFrequencyDecoysQA:
    def test_generator_parse_format_call_frequency_decoys_case(self):
        """
        `Generator.parse` expands `{{ formatter }}` / `{{ formatter:arg_group }}` via
        `re.sub` → `__format_token` → `format`. Each token match invokes `format`
        exactly once. Unused `set_arguments` groups are never read. This test mixes
        overlapping color-related formatters and two integer argument groups with
        deliberate unused groups to stress static analysis.
        """
        Faker.seed(314159)
        fake = Faker()
        fake.set_arguments("rng_lo", {"min_value": 0, "max_value": 9})
        fake.set_arguments("rng_hi", {"min_value": 1000, "max_value": 2000})
        fake.set_arguments("orphan", {"never": "used"})
        fake.set_arguments("decoy", {"x": 1})
        template = (
            "{{ pyint:rng_lo }} {{ pyint:rng_hi }} {{ pyint:rng_lo }} "
            "{{ hex_color }} {{ rgb_color }} {{ rgb_css_color }} "
            "{{ color_name }} {{ pyint:rng_lo }}"
        )
        fake.parse(template)


if __name__ == "__main__":
    t = TestGeneratorParseFormatCallFrequencyDecoysQA()
    t.test_generator_parse_format_call_frequency_decoys_case()
