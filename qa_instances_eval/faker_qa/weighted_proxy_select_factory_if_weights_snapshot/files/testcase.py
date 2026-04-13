from faker import Faker


class TestWeightedProxySelectFactoryIfWeightsSnapshotQA:
    def test_weighted_proxy_select_factory_if_weights_snapshot_case(self):
        """
        Weighted multi-locale `Faker` stores ordered locale weights in `self._weights`.
        A provider call like `word()` is resolved through `Faker.__getattr__` →
        `_select_factory`, which unpacks `(factories, weights)` from `_map_provider_method`
        and then evaluates `if weights:` before choosing between distribution-based or
        uniform factory selection.
        """
        Faker.seed(4242)
        fake = Faker({"en_US": 1, "de_DE": 4, "ja_JP": 9})
        fake.word()


if __name__ == "__main__":
    t = TestWeightedProxySelectFactoryIfWeightsSnapshotQA()
    t.test_weighted_proxy_select_factory_if_weights_snapshot_case()
