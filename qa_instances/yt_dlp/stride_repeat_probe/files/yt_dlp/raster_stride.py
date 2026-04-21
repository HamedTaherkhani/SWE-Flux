"""Raster stride helpers for QA harness fixtures."""

from __future__ import annotations

_tick = 0


def stride_snap(a: int, b: int) -> int:
    global _tick
    _tick += 1
    w = (int(a) & 0xFF) ^ (int(b) & 0xFF)
    core = (w * 41 + 7) & 0xFF
    return (core + _tick) & 0xFF
