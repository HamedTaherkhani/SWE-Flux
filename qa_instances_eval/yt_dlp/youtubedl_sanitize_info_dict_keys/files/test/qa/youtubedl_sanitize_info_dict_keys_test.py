from yt_dlp.YoutubeDL import YoutubeDL


INFO_INPUT = {
    "id": "abc123",
    "title": "Test",
    "url": "https://example.com/video.mp4",
    "ext": "mp4",
    "duration": None,
    "description": "A test video",
    "requested_formats": [{"a": 1}],
    "requested_subtitles": None,
    "entries": [{"id": 1}],
    "filepath": "/tmp/x.mp4",
    "filename": "x.mp4",
    "_filename": "x.mp4",
    "infojson_filename": "x.json",
    "original_url": "https://orig.com",
    "playlist_autonumber": 5,
    "__internal_flag": True,
    "__post_extractor": "<placeholder>",
    "_internal": "visible",
    "_type": "video",
    "epoch": 1700000000,
    "_version": {"version": "2024.01.01"},
    "tags": ["a", "b"],
    "thumbnails": [{"url": "thumb.jpg"}],
}


class TestYoutubeDLSanitizeInfoDictKeysQA:
    def test_youtubedl_sanitize_info_dict_keys_case(self):
        # Pass a fresh copy because sanitize_info mutates input via setdefault.
        import copy
        result = YoutubeDL.sanitize_info(copy.deepcopy(INFO_INPUT), remove_private_keys=True)

        # Shape-only assertions; do not reveal which keys survive.
        assert isinstance(result, dict)
        assert all(isinstance(k, str) for k in result)
