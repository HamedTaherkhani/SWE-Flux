from telegram import MessageEntity


class TestMessageEntityConcatenateDirectOutputQA:
    def test_concatenate_direct_output_case(self):
        first = (
            "prefix alpha beta | ",
            [
                MessageEntity(type=MessageEntity.BOLD, offset=7, length=5),
                MessageEntity(type=MessageEntity.ITALIC, offset=13, length=4),
            ],
            True,
        )
        second = (
            "core block",
            [MessageEntity(type=MessageEntity.CODE, offset=0, length=4)],
            False,
        )
        third = (
            " | suffix zone",
            [MessageEntity(type=MessageEntity.UNDERLINE, offset=3, length=6)],
        )

        combined_text, combined_entities = MessageEntity.concatenate(first, second, third)

        assert isinstance(combined_text, str)
        assert len(combined_entities) == 4
        assert combined_text.startswith("prefix")
        assert combined_entities[2].type == MessageEntity.CODE
