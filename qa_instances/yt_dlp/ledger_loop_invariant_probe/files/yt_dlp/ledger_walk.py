"""Internal QA fixture: ledger walk with a checksum loop used for loop-invariant probes."""

from __future__ import annotations


def ledger_walk(seed: int, token: str) -> int:
    """
    Walk `token` while maintaining a running checksum.

    QA instances target the relationship between `checksum` and the processed prefix of `token`
    inside the `for` loop.
    """
    acc = seed & 0xFFFF
    checksum = 0
    for i, ch in enumerate(token):
        checksum = (checksum + ord(ch)) % 256
        acc = (acc ^ ((ord(ch) + (i * (seed & 0xFF))) & 0xFFFF)) & 0xFFFF
        acc = (acc + ((len(token) ^ i) & 0x7)) & 0xFFFF
    return (acc ^ checksum) & 0xFFFF
