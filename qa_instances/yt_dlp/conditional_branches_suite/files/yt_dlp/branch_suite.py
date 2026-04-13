"""Internal QA fixture: branch-execution probe for conditional suites."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenSpec:
    raw: str
    salt: int

    def as_bytes(self) -> bytes:
        return self.raw.encode("utf-8")


def _mix(seed: int, b: bytes, *, salt: int) -> tuple[int, int, int]:
    acc = seed ^ (salt * 131)
    for i, x in enumerate(b):
        acc = (acc + ((x ^ (i * 17)) * 33)) & 0xFFFFFFFF
    a = (acc ^ (acc >> 11) ^ (len(b) << 9) ^ salt) & 0xFF
    pivot = ((seed * 7 + salt * 5 + len(b) * 19) ^ (acc >> 7)) & 0xFF
    tag = (acc ^ (seed << 3) ^ (salt << 1)) & 0xFF
    return a, pivot, tag


def _classify_token(a: int, pivot: int, tag: int, *, mode: str) -> int:
    """
    Classify (a, pivot, tag) into a small integer in a way that depends on
    mode and on bit-level relationships.
    """
    if (mode in ("auto", "fast") and (a & 1)) or (mode == "strict" and a > pivot):
        out = (a + (pivot ^ tag)) & 0xFF
    elif mode.startswith("x") and (tag % 3 == 0 or (a ^ tag) < 16):
        out = (tag - a + pivot) & 0xFF
    elif (a ^ pivot ^ tag) & 0b10101010:
        out = (a ^ (pivot + tag)) & 0xFF
    else:
        out = (pivot - tag + (a << 1)) & 0xFF

    if out & 0x10:
        out = ((out << 1) ^ (out >> 2) ^ 0x5D) & 0xFF
    else:
        out = ((out >> 1) + (out << 3) + 0x2B) & 0xFF
    return out


def run_suite(seed: int, specs: list[TokenSpec]) -> int:
    total = 0
    for idx, spec in enumerate(specs):
        b = spec.as_bytes()
        a, pivot, tag = _mix(seed + idx * 31, b, salt=spec.salt)
        mode = ("fast" if (tag & 0b0100) else "auto") if (idx % 2 == 0) else "strict"
        if (a ^ pivot) & 0x08:
            mode = "x" + mode
        total ^= _classify_token(a, pivot, tag, mode=mode)
        total = ((total << 3) | (total >> 13)) & 0xFFFF
    return total
