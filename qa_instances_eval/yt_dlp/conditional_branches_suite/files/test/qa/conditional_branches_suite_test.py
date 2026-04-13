from __future__ import annotations

from yt_dlp.branch_suite import TokenSpec, _classify_token, run_suite


class TestConditionalBranchesSuiteQA:
    def test_conditional_branches_suite_part_a(self) -> None:
        specs = [
            TokenSpec("aZ9", salt=7),
            TokenSpec("m1", salt=21),
            TokenSpec("kQ", salt=4),
            TokenSpec("0", salt=15),
        ]
        out = run_suite(0x2A, specs)
        assert isinstance(out, int)
        assert 0 <= out <= 0xFFFF

        extra = 0
        for a, pivot, tag, mode in (
            (5, 200, 1, "auto"),
            (10, 1, 6, "xstrict"),
            (10, 10, 2, "strict"),
            (0, 0, 0, "fast"),
        ):
            extra ^= _classify_token(a, pivot, tag, mode=mode)
        assert isinstance(extra, int)
        assert 0 <= extra <= 0xFF

    def test_conditional_branches_suite_part_b(self) -> None:
        specs = [
            TokenSpec("xY", salt=2),
            TokenSpec("f0o", salt=6),
            TokenSpec("BAR", salt=9),
            TokenSpec("zz", salt=12),
            TokenSpec("q", salt=18),
        ]
        out = run_suite(0x2A, specs)
        assert isinstance(out, int)
        assert 0 <= out <= 0xFFFF
        assert (out ^ 0xBEEF) & 0x7 != 0
