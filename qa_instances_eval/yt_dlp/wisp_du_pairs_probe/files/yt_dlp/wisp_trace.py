"""Wisp trace helpers for QA harness fixtures."""

from __future__ import annotations


def fold_scalar(bias: int, gap: str) -> int:
    x = bias & 0x3F
    y = len(gap)
    t = 0
    if y & 1:
        t = x ^ y
    else:
        t = (x + y) & 0xFF
    z = t
    if z < 14:
        if gap:
            z = (z + ord(gap[0])) & 0xFF
        else:
            z = z + 3
    else:
        z = (z ^ (ord(gap[-1]) if gap else 7)) & 0xFF
    return (z + t) & 0xFF
