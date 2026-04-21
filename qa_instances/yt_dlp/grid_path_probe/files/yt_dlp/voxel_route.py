"""Voxel routing helpers for QA harness fixtures."""

from __future__ import annotations

_phase = 0


def route_cells(u: int, v: int) -> int:
    global _phase
    _phase += 1
    acc = (int(u) & 0xF) ^ (int(v) & 0xF)
    if _phase & 1:
        bump = (acc << 1) ^ 5
        out = bump & 0xFF
    else:
        bump = acc | 0x10
        out = (bump + 1) & 0xFF
    return out
