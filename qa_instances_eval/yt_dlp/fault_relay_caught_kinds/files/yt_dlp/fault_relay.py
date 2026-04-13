"""Fault relay helpers for QA harness fixtures."""

from __future__ import annotations


def absorb_chain(code: int, tag: str) -> int:
    acc = code & 0xFF
    try:
        if tag == "":
            raise ValueError("empty")
        acc += len(tag)
    except ValueError:
        acc = 150
    try:
        if acc > 100:
            raise TypeError("big")
        acc *= 2
    except TypeError:
        acc = (acc + 5) & 0xFF
    try:
        raise OSError(22, "qa")
    except OSError:
        acc ^= 0x0F
    return acc
