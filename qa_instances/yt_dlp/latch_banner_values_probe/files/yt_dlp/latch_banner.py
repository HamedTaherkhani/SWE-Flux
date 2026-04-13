"""Latch banner helpers for QA harness fixtures."""

from __future__ import annotations


def banner_lane(seed: int, key: str) -> int:
    stamp = "__unset__"
    mix = (int(seed) ^ len(key)) & 0x7
    if mix == 0:
        stamp = "QUEUED"
    elif mix == 1:
        stamp = "RUNNING"
    elif mix == 2:
        stamp = "BLOCKED"
    elif mix == 3:
        stamp = "RETRY"
    elif mix == 4:
        stamp = "OK"
    elif mix == 5:
        stamp = "FAIL"
    elif mix == 6:
        stamp = "TIMEOUT"
    else:
        stamp = "UNKNOWN"
    base = sum(ord(c) for c in stamp) + (seed & 0xF) + len(key)
    return base & 0xFF
