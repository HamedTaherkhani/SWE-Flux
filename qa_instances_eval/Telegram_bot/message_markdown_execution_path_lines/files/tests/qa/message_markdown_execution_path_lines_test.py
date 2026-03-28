from datetime import datetime, timezone

from telegram import Chat, Message, MessageEntity, User


class TestMessageMarkdownExecutionPathLinesQA:
    def test_message_markdown_execution_path_lines_case(self):
        parts = {
            "url": "https://ptb.example/path",
            "code": "code_sample",
            "pre": "pre_block",
            "link": "linked_text",
            "mention": "mention_user",
            "strike": "strike_me",
            "under": "under_me",
            "spoiler": "spoiler_me",
            "quote": "quote_line_one\nquote_line_two",
            "nested": "outer_inner_outer",
        }
        joiner = " || "
        text_value = joiner.join(parts[key] for key in parts)

        starts = {}
        cursor = 0
        for key in parts:
            token = parts[key]
            starts[key] = text_value.index(token, cursor)
            cursor = starts[key] + len(token)

        entities_unicode = [
            MessageEntity(type=MessageEntity.URL, offset=starts["url"], length=len(parts["url"])),
            MessageEntity(type=MessageEntity.CODE, offset=starts["code"], length=len(parts["code"])),
            MessageEntity(
                type=MessageEntity.PRE,
                offset=starts["pre"],
                length=len(parts["pre"]),
                language="python",
            ),
            MessageEntity(
                type=MessageEntity.TEXT_LINK,
                offset=starts["link"],
                length=len(parts["link"]),
                url="https://example.org/docs?q=ptb",
            ),
            MessageEntity(
                type=MessageEntity.TEXT_MENTION,
                offset=starts["mention"],
                length=len(parts["mention"]),
                user=User(id=8812, is_bot=False, first_name="Tess"),
            ),
            MessageEntity(
                type=MessageEntity.STRIKETHROUGH,
                offset=starts["strike"],
                length=len(parts["strike"]),
            ),
            MessageEntity(
                type=MessageEntity.UNDERLINE,
                offset=starts["under"],
                length=len(parts["under"]),
            ),
            MessageEntity(
                type=MessageEntity.SPOILER,
                offset=starts["spoiler"],
                length=len(parts["spoiler"]),
            ),
            MessageEntity(
                type=MessageEntity.BLOCKQUOTE,
                offset=starts["quote"],
                length=len(parts["quote"]),
            ),
            MessageEntity(
                type=MessageEntity.BOLD,
                offset=starts["nested"],
                length=len(parts["nested"]),
            ),
            MessageEntity(
                type=MessageEntity.ITALIC,
                offset=starts["nested"] + 6,
                length=5,
            ),
        ]

        entities = MessageEntity.adjust_message_entities_to_utf_16(text_value, entities_unicode)

        message = Message(
            message_id=9201,
            date=datetime(2025, 5, 17, 9, 45, tzinfo=timezone.utc),
            chat=Chat(id=-100772233, type=Chat.SUPERGROUP, title="path_room"),
            from_user=User(id=7781, is_bot=False, first_name="Riley"),
            text=text_value,
            entities=entities,
        )

        markdown_output = message.text_markdown_v2_urled

        assert isinstance(markdown_output, str)
        assert len(markdown_output) > 0
