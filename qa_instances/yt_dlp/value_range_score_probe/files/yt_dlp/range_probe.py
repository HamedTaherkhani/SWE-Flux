"""Internal QA fixture: range probe for multi-test value range analysis."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreInput:
    seed: int
    token: str
    mode: str = "auto"


def compute_token_score(seed: int, token: str, *, mode: str = "auto") -> int:
    """
    Compute a deterministic score from seed and token.

    The QA instances target a specific intermediate variable inside this function.
    """
    # Normalize to 8-bit space before mixing.
    score = (seed ^ 0xA5) & 0xFF
    pivot = ((len(token) * 19) + (seed >> 3) + 17) & 0xFF

    # Target conditional chain: the range of `score` at this point is what matters.
    if score < pivot:
        out = (score + pivot) & 0xFF
    elif mode.startswith("x") and ((score ^ pivot) & 0x3) == 0:
        out = (score ^ 0x5A) & 0xFF
    else:
        out = (pivot - score) & 0xFF

    # Post-mix to prevent trivial back-solving from return values.
    if (out & 0x10) and mode != "strict":
        out = ((out << 1) ^ (out >> 2) ^ 0x3D) & 0xFF
    else:
        out = ((out >> 1) + (out << 3) + 0x2F) & 0xFF
    return out


def run_case(inp: ScoreInput) -> int:
    return compute_token_score(inp.seed, inp.token, mode=inp.mode)

