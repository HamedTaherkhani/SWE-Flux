from __future__ import annotations

import pytest

from yt_dlp.range_probe import ScoreInput, run_case


@pytest.mark.parametrize(
    "inp",
    [
        ScoreInput(seed=int("a5", 16), token="pQ", mode="auto"),
        ScoreInput(seed=int("5a", 16), token="pQ", mode="auto"),
        ScoreInput(seed=(0x1234 ^ 0x10) - 0x1200, token="k", mode="strict"),
        ScoreInput(seed=(1 << 9) + 13, token="xyz", mode="auto"),
        ScoreInput(seed=(7 * 37) ^ 0x99, token="AA", mode="xfast"),
        ScoreInput(seed=(0xDEAD >> 7) & 0x1FF, token="m9_K", mode="auto"),
        ScoreInput(seed=(0xBEEF & 0xFF) | 0x100, token="HELLO", mode="xstrict"),
        ScoreInput(seed=(0xFE ^ 0x21) + 3, token="v", mode="auto"),
        ScoreInput(seed=(0x2A * 11) - 7, token="0", mode="auto"),
        ScoreInput(seed=(0x80 + 0x40 + 0x20) - 1, token="t", mode="strict"),
        ScoreInput(seed=(3 ** 5) + 17, token="stream", mode="auto"),
        ScoreInput(seed=(0x7F << 1) + 1, token="bytes", mode="xauto"),
        ScoreInput(seed=(99 * 3) ^ (17 * 5), token="zz", mode="auto"),
        ScoreInput(seed=(0x1000 // 7) + 6, token="token", mode="xstrict"),
        ScoreInput(seed=(0x3C3C ^ 0x1111) & 0x1FF, token="qqq", mode="auto"),
        ScoreInput(seed=(0x1FF - 0x9A) + 0x2, token="w", mode="auto"),
        ScoreInput(seed=(0x400 >> 2) + (0x33 ^ 0x11), token="unit", mode="strict"),
        ScoreInput(seed=(0x2D * 13) & 0x1FF, token="edge", mode="xfast"),
    ],
)
def test_value_range_score_probe_cases(inp: ScoreInput) -> None:
    out = run_case(inp)
    assert isinstance(out, int)
    assert 0 <= out <= 0xFF

