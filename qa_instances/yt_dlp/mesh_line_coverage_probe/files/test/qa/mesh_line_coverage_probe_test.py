from __future__ import annotations

import pytest

from yt_dlp.switch_mesh import resolve_mesh


@pytest.mark.parametrize(
    ("seed", "slot", "mode"),
    [
        ((0xDEAD ^ 0xDEAD), "", "zeta"),
        ((0x11), "k", "abx"),
        ((0x0E), "uv", "plain"),
        ((0x01), "", "plain"),
        ((0x05), "r", "zztop"),
        ((0x09), "xy", "tailx"),
        ((0x0C), "m", "noop"),
        ((0x15), "ab", "zap"),
        ((0x02), "z", "yx"),
        ((0x10), "qq", "mmx"),
        ((0x07), "", "zx"),
        ((0x16), "t", "oddx"),
        ((0x08), "ab", "seven"),
        ((0x1A), "zz", "zz"),
        ((0x04), "x", "nope"),
        ((0x0B), "yy", "zzx"),
        ((0x12), "a", "zz"),
        ((0x06), "bc", "tailx"),
    ],
)
def test_mesh_line_coverage_probe_cases(seed: int, slot: str, mode: str) -> None:
    out = resolve_mesh(seed, slot, mode)
    assert isinstance(out, int)
    assert 0 <= out <= 0xFF
