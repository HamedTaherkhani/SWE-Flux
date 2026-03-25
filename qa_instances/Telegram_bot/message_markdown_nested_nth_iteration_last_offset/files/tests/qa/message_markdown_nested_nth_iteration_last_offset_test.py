from datetime import datetime, timezone

from telegram import Chat, Message, MessageEntity, User


def _span(text: str, start_token: str, end_token: str) -> tuple[int, int]:
    start = text.index(start_token)
    end = text.index(end_token, start) + len(end_token)
    return start, end - start


class TestMessageMarkdownNestedNthIterationLastOffsetQA:
    def test_message_markdown_nested_nth_iteration_last_offset_case(self):
        text = "alpha 🙂 beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron"

        emoji_offset = text.index("🙂")
        beta_to_theta = _span(text, "beta", "theta")
        gamma_to_epsilon = _span(text, "gamma", "epsilon")
        delta_only = _span(text, "delta", "delta")
        zeta_only = _span(text, "zeta", "zeta")
        eta_to_theta = _span(text, "eta", "theta")
        iota_to_kappa = _span(text, "iota", "kappa")
        kappa_only = _span(text, "kappa", "kappa")
        lambda_only = _span(text, "lambda", "lambda")
        mu_to_xi = _span(text, "mu", "xi")

        unicode_entities = (
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=emoji_offset,
                length=1,
                custom_emoji_id="5368324170671202286",
            ),
            MessageEntity(type=MessageEntity.BOLD, offset=beta_to_theta[0], length=beta_to_theta[1]),
            MessageEntity(
                type=MessageEntity.ITALIC,
                offset=gamma_to_epsilon[0],
                length=gamma_to_epsilon[1],
            ),
            MessageEntity(
                type=MessageEntity.TEXT_LINK,
                offset=delta_only[0],
                length=delta_only[1],
                url="https://example.org/delta",
            ),
            MessageEntity(type=MessageEntity.CODE, offset=zeta_only[0], length=zeta_only[1]),
            MessageEntity(type=MessageEntity.UNDERLINE, offset=eta_to_theta[0], length=eta_to_theta[1]),
            MessageEntity(type=MessageEntity.SPOILER, offset=iota_to_kappa[0], length=iota_to_kappa[1]),
            MessageEntity(type=MessageEntity.BOLD, offset=kappa_only[0], length=kappa_only[1]),
            MessageEntity(type=MessageEntity.URL, offset=lambda_only[0], length=lambda_only[1]),
            MessageEntity(type=MessageEntity.PRE, offset=mu_to_xi[0], length=mu_to_xi[1], language="py"),
        )

        entities = MessageEntity.adjust_message_entities_to_utf_16(text, unicode_entities)

        chat = Chat(id=61234, type=Chat.GROUP, title="qa room")
        user = User(id=61235, first_name="Nora", is_bot=False, username="nora_u")
        message = Message(
            message_id=61236,
            date=datetime(2025, 8, 14, 9, 0, tzinfo=timezone.utc),
            chat=chat,
            from_user=user,
            text=text,
            entities=entities,
        )

        markdown_output = message.text_markdown_v2

        assert isinstance(markdown_output, str)
        assert len(markdown_output) > len(text)
        assert "delta" in markdown_output
        assert "kappa" in markdown_output
