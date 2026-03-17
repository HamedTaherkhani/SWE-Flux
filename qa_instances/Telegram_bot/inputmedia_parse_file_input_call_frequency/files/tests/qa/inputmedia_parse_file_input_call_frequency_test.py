from telegram import (
    InputMediaAnimation,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    InputPaidMediaPhoto,
    InputPaidMediaVideo,
)


class TestInputMediaParseFileInputCallFrequencyQA:
    def test_inputmedia_parse_file_input_call_frequency_case(self):
        media_items = [
            InputMediaPhoto(media=b"photo_a", caption="p1", filename="p1.jpg"),
            InputMediaPhoto(media=b"photo_b", caption="p2", filename="p2.jpg", has_spoiler=True),
            InputMediaPhoto(media=b"photo_c", caption="p3", filename="p3.jpg"),
            InputMediaVideo(
                media=b"video_a",
                filename="v1.mp4",
                width=320,
                height=240,
                duration=7,
                thumbnail=b"thumb_v1",
            ),
            InputMediaVideo(
                media=b"video_b",
                filename="v2.mp4",
                width=640,
                height=360,
                duration=13,
                thumbnail=b"thumb_v2",
                has_spoiler=True,
            ),
            InputMediaVideo(
                media=b"video_c",
                filename="v3.mp4",
                width=800,
                height=450,
                duration=19,
                thumbnail=b"thumb_v3",
            ),
            InputMediaAudio(
                media=b"audio_a",
                filename="a1.mp3",
                title="track-a",
                performer="artist-a",
                duration=5,
                thumbnail=b"thumb_a1",
            ),
            InputMediaAudio(
                media=b"audio_b",
                filename="a2.mp3",
                title="track-b",
                performer="artist-b",
                duration=11,
                thumbnail=b"thumb_a2",
            ),
            InputMediaDocument(
                media=b"doc_a",
                filename="d1.bin",
                caption="doc",
                thumbnail=b"thumb_d1",
                disable_content_type_detection=True,
            ),
            InputMediaAnimation(
                media=b"anim_a",
                filename="an1.gif",
                width=300,
                height=200,
                duration=3,
                thumbnail=b"thumb_an1",
            ),
        ]

        paid_media_items = [
            InputPaidMediaPhoto(media=b"paid_photo_a"),
            InputPaidMediaVideo(
                media=b"paid_video_a",
                width=1280,
                height=720,
                duration=21,
                thumbnail=b"thumb_paid_v1",
                supports_streaming=True,
            ),
        ]

        payload = [item.to_dict() for item in [*media_items, *paid_media_items]]

        assert len(payload) == 12
        assert all(isinstance(item, dict) for item in payload)
        assert all("type" in item for item in payload)
