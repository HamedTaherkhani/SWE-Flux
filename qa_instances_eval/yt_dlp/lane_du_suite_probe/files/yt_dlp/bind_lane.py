"""Bind lane helpers for QA DU-suite coverage fixtures."""

from __future__ import annotations


def tube_digest(seed: int, label: str) -> int:
    acc = seed & 0xFF
    t = len(label)
    hop = 0
    if t == 0:
        hop = 1
    elif t == 1:
        hop = 2
    else:
        hop = 3
    mix = acc ^ hop
    if t == 0:
        mix = (mix + 9) & 0xFF
    elif mix & 1:
        mix = (mix + ord(label[0])) & 0xFF
    else:
        mix = (mix ^ ord(label[-1])) & 0xFF
    out = (mix + t) & 0xFF
    return out
