from collections import OrderedDict

from faker import Faker


class TestUtilsChoicesUniqueNthIterationUniformSampleQA:
    def test_utils_choices_unique_nth_iteration_uniform_sample_case(self):
        """Weighted unique sampling mutates `items`/`probabilities` each iteration; the
        second draw's `uniform_sample` depends on prior RNG use and floating renormalization.
        """
        fake = Faker()
        fake.seed_instance(31337007)
        out = fake.random_elements(
            OrderedDict([("x", 0.1), ("y", 0.2), ("z", 0.3), ("w", 0.4)]),
            length=2,
            unique=True,
        )
        assert out == ["w", "y"]
