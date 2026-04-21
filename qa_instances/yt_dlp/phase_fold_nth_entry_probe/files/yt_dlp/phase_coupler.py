"""Phase-coupled edge folding helpers for timing windows (internal QA fixtures)."""

from __future__ import annotations


def fold_phase_edges(seed: int, label: str) -> int:
    """
    Integrate phase-mixed edge steps until a synthetic bound is reached.

    Strides depend on rotating label bytes, per-iteration bit tests over `seed`,
    and a stable mixing constant derived from label ordinals.
    """
    acc = 0
    cursor = seed % 17
    bound = (len(label) * 3 + seed) % 41 + 12
    phase = sum(ord(c) for c in label) % 5
    k = 0
    while cursor < bound:
        snap = acc
        acc += (cursor ^ phase) & 7
        hop = 2 + (ord(label[k % len(label)]) & 3)
        if (seed >> k) & 1:
            hop += 1
        cursor += hop
        k += 1
    return acc ^ seed
