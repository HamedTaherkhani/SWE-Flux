from __future__ import annotations

import pytest

from yt_dlp.ledger_walk import ledger_walk


@pytest.mark.parametrize(
    ("seed", "token"),
    [
        ((0xDEAD ^ 0xDEAD), ""),
        ((0x10 >> 3), "a"),
        ((0x2 << 1), "ab"),
        ((0x3C ^ 0x3C), "m9_K"),
        ((0x7F & 0x1F), "stream"),
        ((0x100 >> 6), "bytes"),
        ((0x5A5A ^ 0x5A5A), "qqq"),
        ((0x3E8 % 0x7D), "unit"),
        ((0x40 >> 5), "edge"),
        ((0x11 * 0), "x0"),
        ((0x0F ^ 0x0D), "yz"),
        ((0xCC // 0x66), "HELLO"),
        ((0xFE ^ 0xFC), "012"),
        ((0x200 >> 7), "f0o"),
        ((0x33 & 0x0F), "BAR"),
        ((0xAA & 0x55), "zz"),
        ((0x1FF % 0xFD), "q"),
        ((0x18 // 0x0C), "token"),
    ],
)
def test_ledger_loop_invariant_probe_cases(seed: int, token: str) -> None:
    out = ledger_walk(seed, token)
    assert isinstance(out, int)
    assert 0 <= out <= 0xFFFF
