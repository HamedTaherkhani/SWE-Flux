"""Internal QA fixture: cohort label tracing for multi-test value-set analysis."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CohortInput:
    seed: int
    token: str


def trace_cohort_label(seed: int, token: str) -> int:
    """
    Derive a cohort label and return a mixed integer.

    QA instances target the local variable `phase` immediately after it is assigned
    from the `if / elif / else` chain below.
    """
    phase = "UNSET"
    # Non-linear mixing (keeps bucket non-obvious from call sites alone).
    acc = (seed ^ 0x13579BDF) & 0xFFFFFFFF
    acc ^= (len(token) * 0x9E3779B1) & 0xFFFFFFFF
    for i, ch in enumerate(token):
        acc = (acc + (ord(ch) * (i + 11))) ^ (seed << ((i % 3) + 1))
    acc &= 0xFFFFFFFF
    base = ((seed * 3) ^ (len(token) << 4)) & 0xFF
    s = sum(ord(c) for c in token) % 256
    mix = (base + s) % 256
    # Redundant branch (does not change `mix` but adds control-flow noise).
    if (acc & 0x10000) != 0:
        mix = mix ^ 0
    bucket = mix % 6
    if bucket == 0:
        phase = "W0"
    elif bucket == 1:
        phase = "W1"
    elif bucket == 2:
        phase = "W2"
    elif bucket == 3:
        phase = "W3"
    elif bucket == 4:
        phase = "W4"
    else:
        phase = "W5"

    out = (mix ^ (len(phase) * 7) ^ seed) & 0xFFFF
    if phase.endswith("0"):
        out ^= 0x1111
    elif phase.endswith("1"):
        out ^= 0x2222
    else:
        out = (out + ord(phase[-1])) & 0xFFFF
    return out


def run_cohort_case(inp: CohortInput) -> int:
    return trace_cohort_label(inp.seed, inp.token)
