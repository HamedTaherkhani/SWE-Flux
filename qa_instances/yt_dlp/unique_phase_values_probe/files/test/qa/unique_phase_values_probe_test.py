from __future__ import annotations

import pytest

from yt_dlp.cohort_trace import CohortInput, run_cohort_case


def _ch(code: int) -> str:
    return chr(code)


@pytest.mark.parametrize(
    "inp",
    [
        # Three suites over empty token (bucket 0).
        CohortInput(seed=((1 << 12) - (1 << 12)), token=""),
        CohortInput(seed=(0b1010 >> 2), token=""),
        CohortInput(seed=(0x2 << 1), token=""),
        # Three suites over 0x63 ('c') (bucket 1).
        CohortInput(seed=((1 << 12) - (1 << 12)), token=_ch(0x63)),
        CohortInput(seed=(0b1010 >> 2), token=_ch(0x63)),
        CohortInput(seed=(0x2 << 1), token=_ch(0x63)),
        # Three suites over 0x64 ('d') (bucket 2).
        CohortInput(seed=((1 << 12) - (1 << 12)), token=_ch(0x64)),
        CohortInput(seed=(0b1010 >> 2), token=_ch(0x64)),
        CohortInput(seed=(0x2 << 1), token=_ch(0x64)),
        # Three suites over 0x65 ('e') (bucket 3).
        CohortInput(seed=((1 << 12) - (1 << 12)), token=_ch(0x65)),
        CohortInput(seed=(0b1010 >> 2), token=_ch(0x65)),
        CohortInput(seed=(0x2 << 1), token=_ch(0x65)),
        # Three suites over 0x66 ('f') (bucket 4).
        CohortInput(seed=((1 << 12) - (1 << 12)), token=_ch(0x66)),
        CohortInput(seed=(0b1010 >> 2), token=_ch(0x66)),
        CohortInput(seed=(0x2 << 1), token=_ch(0x66)),
        # Three suites over 0x67 ('g') (bucket 5).
        CohortInput(seed=((1 << 12) - (1 << 12)), token=_ch(0x67)),
        CohortInput(seed=(0b1010 >> 2), token=_ch(0x67)),
        CohortInput(seed=(0x2 << 1), token=_ch(0x67)),
    ],
)
def test_unique_phase_values_probe_cases(inp: CohortInput) -> None:
    out = run_cohort_case(inp)
    assert isinstance(out, int)
    assert 0 <= out <= 0xFFFF
