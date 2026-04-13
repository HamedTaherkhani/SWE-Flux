from faker import Faker


class TestSingleLocaleProxyGetattrSelectFactoryReachabilityQA:
    def test_single_locale_proxy_getattr_select_factory_reachability_case(self):
        """
        Default `Faker()` uses a single underlying `Generator`. Attribute resolution
        for provider methods follows `Faker.__getattr__` → `getattr(self._factories[0], attr)`
        and does **not** go through `_select_factory` / `_map_provider_method`, which only
        participate when multiple locale factories exist.
        """
        Faker.seed(999)
        fake = Faker()
        fake.first_name()


if __name__ == "__main__":
    t = TestSingleLocaleProxyGetattrSelectFactoryReachabilityQA()
    t.test_single_locale_proxy_getattr_select_factory_reachability_case()
