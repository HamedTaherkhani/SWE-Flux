from __future__ import annotations

from io import BytesIO

import pytest

from telegram import (
    Animation,
    Audio,
    Document,
    InputMediaAnimation,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    InputPaidMediaPhoto,
    InputPaidMediaVideo,
    InputSticker,
    PhotoSize,
    Video,
)


@pytest.mark.parametrize(
    "case_id",
    [
        "photo_bytes",
        "photo_io",
        "photo_local_path",
        "photo_file_uri",
        "photo_remote_string",
        "photo_photosize_obj",
        "video_bytes_thumb_bytes",
        "video_io_thumb_io",
        "video_local_path_thumb_local_path",
        "video_video_obj",
        "animation_bytes_thumb_bytes",
        "animation_obj_thumb_io",
        "audio_bytes_thumb_bytes",
        "audio_obj_thumb_local_path",
        "document_obj_thumb_io",
        "document_io_thumb_file_uri",
        "paid_photo_bytes",
        "paid_video_io_thumb_uri",
        "sticker_bytes",
        "sticker_local_path",
    ],
)
def test_inputmedia_parse_file_input_line_coverage_suite(case_id: str, tmp_path) -> None:
    media_file = tmp_path / "media_payload.bin"
    media_file.write_bytes(b"payload-123")
    local_path = str(media_file)
    file_uri = media_file.resolve().as_uri()

    if case_id == "photo_bytes":
        obj = InputMediaPhoto(media=b"photo-bytes", caption="c")
    elif case_id == "photo_io":
        obj = InputMediaPhoto(media=BytesIO(b"photo-io"))
    elif case_id == "photo_local_path":
        obj = InputMediaPhoto(media=local_path)
    elif case_id == "photo_file_uri":
        obj = InputMediaPhoto(media=file_uri)
    elif case_id == "photo_remote_string":
        obj = InputMediaPhoto(media="AgACAgQAAxkBAAICV2")
    elif case_id == "photo_photosize_obj":
        photo_obj = PhotoSize(
            file_id="photo_file_id_01",
            file_unique_id="uniq_photo_01",
            width=17,
            height=23,
        )
        obj = InputMediaPhoto(media=photo_obj)
    elif case_id == "video_bytes_thumb_bytes":
        obj = InputMediaVideo(media=b"video-bytes", thumbnail=b"thumb-bytes")
    elif case_id == "video_io_thumb_io":
        obj = InputMediaVideo(media=BytesIO(b"video-io"), thumbnail=BytesIO(b"thumb-io"))
    elif case_id == "video_local_path_thumb_local_path":
        obj = InputMediaVideo(media=local_path, thumbnail=local_path)
    elif case_id == "video_video_obj":
        video_obj = Video(
            file_id="video_file_id_01",
            file_unique_id="uniq_video_01",
            width=320,
            height=180,
            duration=11,
        )
        obj = InputMediaVideo(media=video_obj, thumbnail="http://example.com/t.jpg")
    elif case_id == "animation_bytes_thumb_bytes":
        obj = InputMediaAnimation(media=b"anim-bytes", thumbnail=b"anim-thumb")
    elif case_id == "animation_obj_thumb_io":
        animation_obj = Animation(
            file_id="anim_file_id_01",
            file_unique_id="uniq_anim_01",
            width=100,
            height=60,
            duration=4,
        )
        obj = InputMediaAnimation(media=animation_obj, thumbnail=BytesIO(b"anim-thumb-io"))
    elif case_id == "audio_bytes_thumb_bytes":
        obj = InputMediaAudio(media=b"audio-bytes", thumbnail=b"audio-thumb")
    elif case_id == "audio_obj_thumb_local_path":
        audio_obj = Audio(
            file_id="audio_file_id_01",
            file_unique_id="uniq_audio_01",
            duration=7,
            performer="ptb",
            title="qa",
        )
        obj = InputMediaAudio(media=audio_obj, thumbnail=local_path)
    elif case_id == "document_obj_thumb_io":
        document_obj = Document(
            file_id="doc_file_id_01",
            file_unique_id="uniq_doc_01",
            file_name="x.txt",
        )
        obj = InputMediaDocument(media=document_obj, thumbnail=BytesIO(b"doc-thumb"))
    elif case_id == "document_io_thumb_file_uri":
        obj = InputMediaDocument(media=BytesIO(b"doc-io"), thumbnail="file:///tmp/doc-thumb.jpg")
    elif case_id == "paid_photo_bytes":
        obj = InputPaidMediaPhoto(media=b"paid-photo")
    elif case_id == "paid_video_io_thumb_uri":
        obj = InputPaidMediaVideo(media=BytesIO(b"paid-video"), thumbnail="file:///tmp/paid-thumb.png")
    elif case_id == "sticker_bytes":
        obj = InputSticker(sticker=b"sticker-bytes", emoji_list=["🙂"], format="static")
    elif case_id == "sticker_local_path":
        obj = InputSticker(sticker=local_path, emoji_list=["🙂"], format="video")
    else:
        raise AssertionError(f"unexpected case_id: {case_id}")

    assert obj is not None
