from datetime import datetime, timezone

from telegram import Update


class TestChatMemberUpdatedDifferenceStateQA:
    def test_loop_conditional_markdown_state_case(self):
        token = "loop-conditional-markdown-state"
        seed = sum((idx + 9) * ord(char) for idx, char in enumerate(token))

        update_id = 890000000 + (seed % 100000)
        message_id = 600 + (seed % 120)
        msg_date = int(datetime(2024, 8, 17, 15, 0, tzinfo=timezone.utc).timestamp()) + (seed % 90)

        text_value = "alpha beta gamma delta epsilon"
        raw_update = {
            "update_id": update_id,
            "message": {
                "message_id": message_id,
                "date": msg_date,
                "chat": {"id": -100990011, "type": "supergroup", "title": "md_loop_room"},
                "from": {"id": 42001, "is_bot": False, "first_name": "Loop"},
                "text": text_value,
                "entities": [
                    {"type": "bold", "offset": 0, "length": 16},
                    {"type": "italic", "offset": 6, "length": 4},
                    {"type": "code", "offset": 11, "length": 5},
                    {"type": "url", "offset": 17, "length": 5},
                ],
            },
            "callback_query": {
                "id": f"cq-loop-{seed % 1000}",
                "from": {"id": 42002, "is_bot": False, "first_name": "Caller"},
                "chat_instance": f"loopinst-{seed % 7000}",
                "data": f"flow:{seed % 101}",
                "message": {
                    "message_id": message_id + 3,
                    "date": msg_date + 9,
                    "chat": {"id": -100990011, "type": "supergroup", "title": "md_loop_room"},
                    "from": {"id": 42003, "is_bot": False, "first_name": "Branch"},
                    "text": "aux callback text",
                },
            },
            "poll": {
                "id": f"poll-loop-{seed % 100}",
                "question": "pick",
                "options": [{"text": "left", "voter_count": 3}, {"text": "right", "voter_count": 5}],
                "total_voter_count": 8,
                "is_closed": False,
                "is_anonymous": True,
                "type": "regular",
                "allows_multiple_answers": False,
            },
        }

        update_obj = Update.de_json(raw_update, None)
        message_obj = update_obj.message
        markdown_v2 = message_obj.text_markdown_v2

        assert isinstance(markdown_v2, str)
        assert "epsilon" in markdown_v2
        assert "delta" in markdown_v2
        assert "`gamma`" in markdown_v2
