from datetime import datetime, timezone
import re

from telegram import Chat, Message, MessageEntity, User


class TestMessageQuoteEntitiesSizeQA:
    def test_quote_entities_size_case(self):
        text_value = "alpha beta gamma delta beta gamma epsilon beta gamma zeta"
        quote_text = "beta gamma"

        quote_occurrences = [m.start() for m in re.finditer(re.escape(quote_text), text_value)]
        target_index = (len(text_value) + len(quote_occurrences)) % len(quote_occurrences)
        target_start = quote_occurrences[target_index]

        candidate_spans = [
            (target_start - 8, 18),
            (target_start - 4, 16),
            (target_start, len(quote_text)),
            (target_start + 2, 7),
            (target_start + 5, 4),
            (target_start - 1, 12),
            (quote_occurrences[0], len(quote_text)),
            (quote_occurrences[1] - 3, 8),
            (0, 5),
            (len(text_value) - 4, 4),
        ]

        entity_types = [
            MessageEntity.BOLD,
            MessageEntity.ITALIC,
            MessageEntity.CODE,
            MessageEntity.UNDERLINE,
            MessageEntity.SPOILER,
            MessageEntity.STRIKETHROUGH,
        ]

        entities_unicode = []
        for idx, (offset, length) in enumerate(candidate_spans):
            if offset < 0 or offset + length > len(text_value):
                continue
            entities_unicode.append(
                MessageEntity(offset=offset, length=length, type=entity_types[idx % len(entity_types)])
            )

        entities = MessageEntity.adjust_message_entities_to_utf_16(text_value, entities_unicode)

        message = Message(
            message_id=712,
            date=datetime(2025, 2, 12, 18, 20, tzinfo=timezone.utc),
            chat=Chat(id=-100887799, type=Chat.SUPERGROUP, title="quote_room"),
            from_user=User(id=99001, is_bot=False, first_name="Quote"),
            text=text_value,
            entities=entities,
        )

        reply_kwargs = message.build_reply_arguments(
            quote=quote_text,
            quote_index=target_index,
            target_chat_id=message.chat_id,
            allow_sending_without_reply=True,
        )

        assert isinstance(reply_kwargs, dict)
        assert "reply_parameters" in reply_kwargs
        assert reply_kwargs["chat_id"] == message.chat_id
