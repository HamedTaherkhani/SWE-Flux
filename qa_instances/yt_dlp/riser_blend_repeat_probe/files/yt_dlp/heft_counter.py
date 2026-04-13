"""Heft counter helpers for QA harness fixtures."""

from __future__ import annotations

_lane_mix = 0


def blend_quota(seed: int, span: int) -> int:
    """Blend seed and span into an unsigned byte-sized quota."""
    global _lane_mix
    _lane_mix = (_lane_mix + 0x1B) & 0xFF
    core = ((seed & 0xFF) ^ (span & 0xFF) ^ _lane_mix) & 0xFF
    if (seed + span) & 1:
        fold = (core + ((seed >> 2) & 7)) & 0xFF
    else:
        fold = (core - (span % 5)) & 0xFF
    return fold
