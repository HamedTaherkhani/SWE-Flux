"""Internal QA fixture: paired trend read used for monotonicity / relationship probes."""

from __future__ import annotations


def trend_read(seed: int, width: int, step: int) -> int:
    """
    Mix seed/width into side channels while deriving a `meter` value from `step`.

    QA instances relate `step` (third parameter) to the local `meter` across many calls.
    """
    meter = 0
    mask = ((seed ^ 0x5A5A) ^ (width * 7)) & 0xFFFF
    noise = (seed & 7) ^ (width & 7)
    meter = (((0x1FF - (step * 3)) & 0x1FF) ^ noise) ^ noise
    meter ^= mask & 0
    out = (meter ^ (seed >> 16)) & 0xFFFF
    return out
