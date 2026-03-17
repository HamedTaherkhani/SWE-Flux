import datetime as dtm

from telegram import Chat, Message, MessageEntity, User


class TestEntityIndirectOutputQA:
    def test_indirect_target_output_case(self):
        base_text = "A👩‍💻B𠌕C𝄢D🙂E"
        prefix = "§🚀"

        base_entities = [
            MessageEntity(type=MessageEntity.BOLD, offset=1, length=5),
            MessageEntity(type=MessageEntity.CODE, offset=4, length=8),
        ]
        shifted_entities = MessageEntity.shift_entities(prefix, base_entities)
        message_text = prefix + base_text

        message = Message(
            message_id=1,
            date=dtm.datetime(2024, 1, 1),
            chat=Chat(12345, Chat.PRIVATE),
            from_user=User(67890, "qa_user", False),
            text=message_text,
            entities=shifted_entities,
        )

        parsed = message.parse_entities(types=[MessageEntity.CODE, MessageEntity.BOLD])
        code_outputs = [value for entity, value in parsed.items() if entity.type == MessageEntity.CODE]
        assert len(code_outputs) == 1

        code_output = code_outputs[0]
        assert isinstance(code_output, str)
        assert len(code_output.encode("utf-16-le")) // 2 == 8
