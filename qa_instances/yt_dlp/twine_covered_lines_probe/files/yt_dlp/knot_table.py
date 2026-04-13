"""Knot table helpers for QA harness fixtures."""

from __future__ import annotations


def resolve_knot(warp: int, weft: str, tag: str) -> int:
    a = warp & 0x1F
    b = len(weft)
    c = len(tag)
    acc = (a ^ b) & 0xFF
    if acc & 1:
        acc = (acc + c) & 0xFF
    else:
        acc = (acc - (c % 5)) & 0xFF
    if b == 0:
        acc = (acc ^ 0x3C) & 0xFF
    elif b == 1:
        acc = (acc + ord(weft[0])) & 0xFF
    else:
        if tag:
            acc = (acc ^ ord(tag[0])) & 0xFF
        else:
            acc = (acc + 11) & 0xFF
    if warp > 0x7FFFFFFF:
        acc = 99
    return acc & 0xFF
