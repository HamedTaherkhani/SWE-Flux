"""Radix-oriented stride helpers for chunked codec emulation (internal QA fixtures)."""

from __future__ import annotations


def merge_stride_totals(state: int, blob: str) -> int:
    """
    Walk a synthetic bounded index with state- and payload-dependent strides.

    The control structure is intentionally non-uniform: step width depends on
    shifting `state`, digit checks on the rotating `blob` character, and a
    parity gate tied to the low bits of `state`.
    """
    acc = 0
    i = 0
    raw = (state ^ len(blob)) & 63
    limit = max(raw, 8)
    wheel = sum(ord(c) for c in blob) % 7
    parity = state & 3
    while i < limit:
        acc = (acc + (i ^ wheel)) & 0xFFFFFFFF
        step = 1 + ((state >> (i % 5)) & 3)
        if parity == (i & 3):
            step += 2
        if blob[i % len(blob)] in "2468":
            step = max(step - 1, 1)
        if i + step > limit:
            step = limit - i
        i += step
    return acc ^ state
