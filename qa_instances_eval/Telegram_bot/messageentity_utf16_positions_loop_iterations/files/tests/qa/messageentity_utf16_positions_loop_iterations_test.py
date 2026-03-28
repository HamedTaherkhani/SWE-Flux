from telegram import MessageEntity


class TestMessageEntityUtf16PositionsLoopIterationsQA:
    def test_messageentity_utf16_positions_loop_iterations_case(self):
        text = "𝄢ab𠌕cdEFghIJklMNopQRstUVwxYZ12"

        entities = [
            MessageEntity(type=MessageEntity.BOLD, offset=0, length=4),
            MessageEntity(type=MessageEntity.ITALIC, offset=3, length=5),
            MessageEntity(type=MessageEntity.UNDERLINE, offset=8, length=4),
            MessageEntity(type=MessageEntity.STRIKETHROUGH, offset=10, length=6),
            MessageEntity(type=MessageEntity.SPOILER, offset=15, length=3),
            MessageEntity(type=MessageEntity.CODE, offset=18, length=5),
            MessageEntity(type=MessageEntity.BLOCKQUOTE, offset=22, length=4),
            MessageEntity(type=MessageEntity.PRE, offset=24, length=5, language="py"),
            MessageEntity(type=MessageEntity.BOLD, offset=26, length=4),
        ]

        converted = MessageEntity.adjust_message_entities_to_utf_16(text, entities)

        assert len(converted) == len(entities)
        assert all(e.length > 0 for e in converted)
        assert all(e.offset >= 0 for e in converted)
