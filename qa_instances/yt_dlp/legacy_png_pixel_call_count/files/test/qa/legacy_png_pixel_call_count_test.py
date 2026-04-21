import struct
import zlib

from yt_dlp.utils._legacy import decode_png


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    # CRC is not validated by decode_png; we can use zeroes deterministically.
    return struct.pack(">I", len(data)) + chunk_type + data + b"\x00\x00\x00\x00"


class TestLegacyPngPixelCallCountQA:
    def test_legacy_png_pixel_call_count_case(self) -> None:
        width, height = 2, 2
        ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)

        stride = width * 3
        raw = bytes([0]) + bytes(range(1, 1 + stride)) + bytes([4]) + bytes(range(10, 10 + stride))
        compressed = zlib.compress(raw)

        png = (
            b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", ihdr)
            + _png_chunk(b"IDAT", compressed)
            + _png_chunk(b"IEND", b"")
        )

        out_width, out_height, pixels = decode_png(png)
        assert (out_width, out_height) == (2, 2)
        assert len(pixels) == 2
