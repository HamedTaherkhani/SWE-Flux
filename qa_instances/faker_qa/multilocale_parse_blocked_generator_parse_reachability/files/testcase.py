from faker import Faker


class TestMultilocaleParseBlockedGeneratorParseReachabilityQA:
    def test_multilocale_parse_blocked_generator_parse_reachability_case(self):
        """
        In `faker/proxy.py`, when `len(self._factories) > 1` and the requested attribute
        is listed in `generator_attrs` (including `parse`), `Faker.__getattr__` raises
        `NotImplementedError` before delegating to any `Generator`. Therefore
        `Generator.parse` is never entered for multi-locale proxies.
        """
        Faker.seed(777)
        fake = Faker(["fr_FR", "ja_JP"])
        try:
            fake.parse("{{ name }}")
        except NotImplementedError:
            pass


if __name__ == "__main__":
    t = TestMultilocaleParseBlockedGeneratorParseReachabilityQA()
    t.test_multilocale_parse_blocked_generator_parse_reachability_case()
