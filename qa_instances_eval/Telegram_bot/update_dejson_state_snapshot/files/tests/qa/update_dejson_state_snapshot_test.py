from telegram import Update


class TestUpdateDejsonStateSnapshotQA:
    def test_update_dejson_state_snapshot_case(self):
        raw_update = {
            "update_id": 987654321,
            "message": {
                "message_id": 100,
                "date": 1700000000,
                "chat": {"id": -100123, "type": "supergroup", "title": "qa_group"},
                "from": {"id": 42, "is_bot": False, "first_name": "Ada", "username": "ada_user"},
                "text": "alpha beta gamma",
                "entities": [{"type": "bold", "offset": 6, "length": 4}],
            },
            "edited_message": {
                "message_id": 101,
                "date": 1700000100,
                "chat": {"id": -100123, "type": "supergroup", "title": "qa_group"},
                "from": {"id": 43, "is_bot": False, "first_name": "Bob"},
                "text": "delta epsilon",
            },
            "callback_query": {
                "id": "cbq-1",
                "from": {"id": 44, "is_bot": False, "first_name": "Cid"},
                "chat_instance": "inst-1",
                "data": "pick:2",
                "message": {
                    "message_id": 102,
                    "date": 1700000200,
                    "chat": {"id": -100123, "type": "supergroup", "title": "qa_group"},
                    "from": {"id": 45, "is_bot": False, "first_name": "Di"},
                    "text": "button message",
                },
            },
            "poll": {
                "id": "poll-1",
                "question": "choose",
                "options": [
                    {"text": "optA", "voter_count": 2},
                    {"text": "optB", "voter_count": 5},
                ],
                "total_voter_count": 7,
                "is_closed": False,
                "is_anonymous": True,
                "type": "regular",
                "allows_multiple_answers": False,
            },
            "chat_member": {
                "chat": {"id": -100123, "type": "supergroup", "title": "qa_group"},
                "from": {"id": 46, "is_bot": False, "first_name": "Eve"},
                "date": 1700000300,
                "old_chat_member": {
                    "status": "member",
                    "user": {"id": 50, "is_bot": False, "first_name": "Frank"},
                },
                "new_chat_member": {
                    "status": "administrator",
                    "user": {"id": 50, "is_bot": False, "first_name": "Frank"},
                    "can_be_edited": True,
                    "is_anonymous": False,
                    "can_manage_chat": True,
                    "can_delete_messages": True,
                    "can_manage_video_chats": False,
                    "can_restrict_members": True,
                    "can_promote_members": False,
                    "can_change_info": True,
                    "can_invite_users": True,
                    "can_post_stories": False,
                    "can_edit_stories": False,
                    "can_delete_stories": False,
                },
            },
        }

        update_obj = Update.de_json(raw_update, None)
        state_dict = update_obj.to_dict()

        assert isinstance(state_dict, dict)
        assert "update_id" in state_dict
        assert "message" in state_dict
        assert "poll" in state_dict
        assert "chat_member" in state_dict
