"""Internal QA fixture: binding flux with a local modulus used for invariant probes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FluxBind:
    """Stateful binder used only by QA fixtures."""

    tag: int = 0

    def bind(self, seed: int, token: str) -> int:
        scratch = 0
        acc = (seed ^ 0x13579BDF) & 0xFFFFFFFF
        acc ^= (len(token) * 0x9E3779B1) & 0xFFFFFFFF
        for i, ch in enumerate(token):
            acc = (acc + (ord(ch) * (i + 11))) ^ (seed << ((i % 3) + 1))
        acc &= 0xFFFFFFFF
        lane = (acc ^ (acc >> 11) ^ (acc >> 22)) & 0xFF
        pivot = ((len(token) * 19) ^ (seed >> 3)) & 0xFF
        # Local modulus used in the XOR at exit; never reassigned after this point.
        m = 13
        if lane < pivot and (seed & 0x01) == 0:
            scratch = (lane + pivot + (seed & 0xFF)) & 0xFFFF
        elif lane < pivot:
            scratch = (pivot - lane + (len(token) << 2)) & 0xFFFF
        elif (lane ^ pivot) & 0x08:
            scratch = (lane + (seed & 0xFF)) & 0xFFFF
        elif token.startswith("x") or token.endswith("z"):
            scratch = ((lane * 3) ^ pivot) & 0xFFFF
        else:
            scratch = (
                (lane ^ pivot ^ (seed & 0xF)) + ((acc >> 16) & 0xFF)
            ) & 0xFFFF
        # Extra mixing that does not reassign `m`.
        if (scratch & 0x1000) != 0:
            scratch = (scratch ^ (m >> 1)) & 0xFFFF
        else:
            scratch = (scratch + (m << 1)) & 0xFFFF
        self.tag = (self.tag ^ scratch) & 0xFFFF
        return (scratch ^ m) & 0xFFFF
