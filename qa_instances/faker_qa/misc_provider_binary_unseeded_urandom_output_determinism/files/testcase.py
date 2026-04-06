from faker import Faker


class TestMiscProviderBinaryUrandomOutputDeterminismQA:
    def test_misc_provider_binary_unseeded_urandom_output_determinism_case(self):
        """
        Unseeded `binary` takes the `os.urandom` fast path (`_is_seeded` is false),
        so each process observes OS entropy — outputs are not reproducible across
        independent pytest invocations even though the call site is identical.
        """
        fake = Faker()
        fake.binary(48)


if __name__ == "__main__":
    t = TestMiscProviderBinaryUrandomOutputDeterminismQA()
    t.test_misc_provider_binary_unseeded_urandom_output_determinism_case()
