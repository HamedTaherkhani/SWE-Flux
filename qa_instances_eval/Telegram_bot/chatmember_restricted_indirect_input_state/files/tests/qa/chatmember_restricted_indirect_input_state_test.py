from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from telegram import ChatMember


class _QADefaults:
    def __init__(self, tzinfo):
        self.tzinfo = tzinfo


class _QABot:
    def __init__(self, tzinfo):
        self.defaults = _QADefaults(tzinfo=tzinfo)


class TestChatMemberRestrictedIndirectInputStateQA:
    def test_chatmember_restricted_indirect_input_state_case(self):
        token = "member-restriction-flow"
        seed = sum((idx + 5) * ord(char) for idx, char in enumerate(token))

        base_ts = int(datetime(2025, 2, 14, 7, 30, tzinfo=timezone.utc).timestamp())
        until_date_value = base_ts + (seed % 2048) - 137
        user_id_value = 770000 + ((seed // 3) % 10000)

        core_permissions = {
            "is_member": True,
            "can_change_info": False,
            "can_invite_users": True,
            "can_pin_messages": False,
            "can_send_messages": True,
            "can_send_polls": False,
            "can_send_other_messages": True,
            "can_add_web_page_previews": False,
            "can_manage_topics": True,
        }
        media_permissions = {
            "can_send_audios": True,
            "can_send_documents": False,
            "can_send_photos": True,
            "can_send_videos": False,
            "can_send_video_notes": True,
            "can_send_voice_notes": False,
        }

        raw_member = {
            "status": "restricted",
            "user": {
                "id": user_id_value,
                "is_bot": False,
                "first_name": "Flow",
                "username": "state_probe",
            },
            "until_date": until_date_value,
            "can_send_media_messages": False,
            **core_permissions,
            **media_permissions,
        }

        bot = _QABot(tzinfo=ZoneInfo("Asia/Kathmandu"))
        parsed_member = ChatMember.de_json(raw_member, bot)

        assert parsed_member.status == ChatMember.RESTRICTED
        assert parsed_member.user.id == user_id_value
        assert parsed_member.can_manage_topics is True
        assert parsed_member.api_kwargs.get("can_send_media_messages") is False
