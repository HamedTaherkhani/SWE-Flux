import io
from pathlib import Path

import pytest

from telegram._utils.files import parse_file_input


class DummyTelegramMedia:
    def __init__(self, file_id: str):
        self.file_id = file_id


class TestParseFileInputDefUsePairsQA:
    def test_parse_file_input_def_use_pairs_case(self, tmp_path: Path):
        local_path = tmp_path / "sample.bin"
        local_path.write_bytes(b"content")

        out1 = parse_file_input(str(local_path), attach=True, local_mode=False)
        out2 = parse_file_input(str(local_path), attach=False, local_mode=True)
        out3 = parse_file_input(b"raw-bytes", filename="blob.dat", attach=True)
        out4 = parse_file_input(io.BytesIO(b"stream-bytes"), filename="stream.dat", attach=False)
        out5 = parse_file_input("https://example.org/file.bin", local_mode=False)
        out6 = parse_file_input(DummyTelegramMedia("TG_FILE_123"), tg_type=DummyTelegramMedia)

        with pytest.raises(ValueError):
            parse_file_input("file:///tmp/forbidden.bin", local_mode=False)

        out7 = parse_file_input("file:///tmp/allowed.bin", local_mode=True)

        assert out1 is not None
        assert out2.startswith("file://")
        assert out3 is not None
        assert out4 is not None
        assert out5 == "https://example.org/file.bin"
        assert out6 == "TG_FILE_123"
        assert out7 == "file:///tmp/allowed.bin"
