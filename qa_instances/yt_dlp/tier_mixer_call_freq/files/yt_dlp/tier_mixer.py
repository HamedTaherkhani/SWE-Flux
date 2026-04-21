"""Tier mixing helpers for QA harness fixtures."""

from __future__ import annotations


def merge_ticks(seed: int, parts: tuple[str, ...]) -> int:
    def bump(c: str) -> int:
        return (ord(c) & 0xF) ^ (ord(c) >> 4 & 0xF)

    acc = int(seed) & 0xFF
    for p in parts:
        for ch in p:
            acc = (acc + bump(ch)) & 0xFF
        if len(p) >= 2:
            acc = (acc ^ bump(p[0])) & 0xFF
            acc = (acc ^ bump(p[-1])) & 0xFF
    return acc
