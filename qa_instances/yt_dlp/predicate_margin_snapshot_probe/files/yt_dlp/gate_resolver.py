"""Gate resolution helpers for span-bound codec checks (internal QA fixtures)."""

from __future__ import annotations


def resolve_gate_span(seed: int, token: str) -> int:
    """
    Fold seed and token into a gate decision using a skewed comparison.

    Strides mix low-bit masks, ordinal sums, and modular wrap so the decisive
    comparison is not obvious from the call arguments alone.
    """
    x = ((seed * 3) ^ (len(token) << 4)) & 0x1FF
    threshold = (sum(ord(c) for c in token) % 17) + (seed >> 2) % 9
    x += (ord(token[0]) if token else 0) & 31
    threshold = (threshold * 2 - len(token)) % 200
    if x > threshold:
        return (x + threshold) % 1000
    return (x - threshold) % 1000
