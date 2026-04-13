"""Hinge cascade helpers for QA harness fixtures."""

from __future__ import annotations


def inner_blend(acc: int, slot: int, flag: bool) -> int:
    mix = (acc ^ slot) if flag else (acc + slot)
    return mix & 0xFF


def outer_wire(k: int, tag: str) -> int:
    base = (k & 0x7F) ^ (len(tag) << 2)
    if k & 8:
        acc = (base + ord(tag[0])) & 0xFF if tag else base & 0xFF
    else:
        acc = (base - (ord(tag[-1]) if tag else 0)) & 0xFF
    slot = (k + len(tag)) & 0xFF
    flag = acc < slot
    return inner_blend(acc, slot, flag)
