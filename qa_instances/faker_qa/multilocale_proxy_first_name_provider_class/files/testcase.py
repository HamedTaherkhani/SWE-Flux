from faker import Faker


class TestMultilocaleProxyFirstNameProviderClassQA:
    def test_multilocale_proxy_first_name_provider_class_case(self):
        """
        Multi-locale Faker dispatches provider methods through `Faker.__getattr__` →
        `_select_factory` → `_map_provider_method` → `_select_factory_choice` (or
        weighted distribution). Factory choice uses the shared module-level RNG in
        `faker.generator.random`, which must be seeded via `Faker.seed(...)` for a
        deterministic locale selection before `first_name()` is invoked.
        """
        Faker.seed(1337)
        fake = Faker(["en_US", "de_DE", "ja_JP", "fr_FR"])
        fake.first_name()


if __name__ == "__main__":
    t = TestMultilocaleProxyFirstNameProviderClassQA()
    t.test_multilocale_proxy_first_name_provider_class_case()
