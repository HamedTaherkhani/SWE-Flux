import datetime as dtm

from telegram import Chat, Message, MessageEntity, User


class TestMarkdownIndirectOutputQA:
    def test_markdown_v2_indirect_target_output_case(self):
        text = "start bold and italic end plus http://example.com/a_b and code x_y"
        entities = [
            MessageEntity(MessageEntity.BOLD, offset=6, length=15),
            MessageEntity(MessageEntity.ITALIC, offset=15, length=6),
            MessageEntity(MessageEntity.URL, offset=31, length=22),
            MessageEntity(MessageEntity.CODE, offset=63, length=3),
        ]

        message = Message(
            message_id=1,
            date=dtm.datetime(2024, 1, 1),
            chat=Chat(11111, Chat.PRIVATE),
            from_user=User(22222, "qa_user_two", False),
            text=text,
            entities=entities,
        )

        markdown_output = message.text_markdown_v2_urled
        assert isinstance(markdown_output, str)
        assert "http://example.com/a_b" in markdown_output
        assert "`x_y`" in markdown_output
