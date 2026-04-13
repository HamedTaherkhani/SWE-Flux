import pytest
from faker import Faker


class TestEmojiProviderEmptyEmojisIndexErrorUncaughtQA:
    def test_emoji_provider_empty_emojis_indexerror_uncaught_case(self):
        """
        Sample emoji output under a fixed seed, touch unrelated formatters to advance
        generator state, then clear `emojis` so `Provider.emoji` cannot sample.
        """
        fake = Faker()
        fake.seed_instance(3141)
        fake.emoji()
        fake.word()
        fake.emoji()
        emoji_provider = fake.provider("faker.providers.emoji")
        assert emoji_provider is not None
        emoji_provider.emojis = ()
        with pytest.raises(IndexError) as exc_info:
            fake.emoji()
        print(f"EXCEPTION {type(exc_info.value).__name__}: {exc_info.value!r}")


if __name__ == "__main__":
    t = TestEmojiProviderEmptyEmojisIndexErrorUncaughtQA()
    t.test_emoji_provider_empty_emojis_indexerror_uncaught_case()
