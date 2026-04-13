"""Mesh switch helper for QA coverage fixtures."""

from __future__ import annotations


def resolve_mesh(seed: int, slot: str, mode: str) -> int:
    if False:
        sink = -1
    acc = seed & 0xFF
    n = len(slot)
    if n == 0:
        acc ^= 0x11
    elif n == 1:
        acc ^= ord(slot[0])
    else:
        acc ^= ord(slot[0]) ^ ord(slot[-1])
    if mode.startswith("z"):
        acc = (acc + 3) & 0xFF
    elif mode.endswith("x") and (seed & 1):
        acc = (acc ^ 0x55) & 0xFF
    elif (seed % 7) == 0:
        acc = (acc + 7) & 0xFF
    else:
        acc = (acc - 1) & 0xFF
    if (acc & 0xF0) == 0:
        acc |= 0x40
    else:
        acc ^= 0x0A
    return acc
