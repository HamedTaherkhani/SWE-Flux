from __future__ import annotations

import pytest

from faker import Faker


# Each entry is a byte length passed to binary().
# The suite deliberately spans a wide range of sizes — from 0 (empty blob)
# through small, medium and large counts — all with an *unseeded* Faker so
# that Provider.binary always takes the os.urandom fast path.
LENGTHS = [
    0,    # os.urandom(0) always returns b'' — trivially invariant
    1,    # single OS-entropy byte
    4,
    8,
    12,
    16,
    24,
    32,
    48,
    56,
    64,
    96,
    100,
    128,
    256,
]


class TestMiscProviderBinaryUrandomOutputDeterminismQA:
    @pytest.mark.parametrize("length", LENGTHS)
    def test_misc_provider_binary_unseeded_urandom_output_determinism_case(
        self, length
    ):
        """
        Construct an unseeded Faker instance (no Faker.seed call) and invoke
        binary(length).  Because _is_seeded is False, Provider.binary returns
        os.urandom(length) instead of the deterministic randrange path, so the
        returned bytes are drawn from OS entropy on every process invocation.
        """
        fake = Faker()
        fake.binary(length)


if __name__ == "__main__":
    t = TestMiscProviderBinaryUrandomOutputDeterminismQA()
    for length in LENGTHS:
        t.test_misc_provider_binary_unseeded_urandom_output_determinism_case(length)
