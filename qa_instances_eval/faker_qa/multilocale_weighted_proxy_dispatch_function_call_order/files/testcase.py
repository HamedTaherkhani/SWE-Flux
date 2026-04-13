from faker import Faker


class TestMultilocaleWeightedProxyDispatchFunctionCallOrderQA:
    def test_multilocale_weighted_proxy_dispatch_function_call_order_case(self):
        """
        Weighted multi-locale `Faker` stores per-locale weights and, when more than one
        locale exposes a method, `_select_factory` uses `_select_factory_distribution`
        (via `choices_distribution`) instead of `_select_factory_choice`. Each distinct
        provider method name (`first_name`, `last_name`, `name`) goes through
        `_map_provider_method` (with per-method caching on the proxy).
        """
        Faker.seed(424242)
        fake = Faker({"en_US": 5, "de_DE": 15, "it_IT": 25})
        fake.first_name()
        fake.last_name()
        fake.name()


if __name__ == "__main__":
    t = TestMultilocaleWeightedProxyDispatchFunctionCallOrderQA()
    t.test_multilocale_weighted_proxy_dispatch_function_call_order_case()
