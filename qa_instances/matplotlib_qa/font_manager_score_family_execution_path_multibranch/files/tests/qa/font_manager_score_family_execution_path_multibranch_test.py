#!/usr/bin/env python3
"""
Direct FontManager.score_family calls with disjoint branches: empty-family early exit,
failed scan with final miss, generic-alias resolution with index, and plain name match.
"""
import importlib
import os
import sys
from pathlib import Path

_testbed_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_testbed_root / "lib"))
os.environ.setdefault("MPLBACKEND", "Agg")

_fm = importlib.import_module("matplotlib.font_manager")


class TestFontManagerScoreFamilyExecutionPathMultibranchQA:
    def test_font_manager_score_family_execution_path_multibranch_case(self):
        fm = _fm.fontManager

        # (1) Empty family list -> early return at len==0 branch.
        fm.score_family((), "DejaVu Sans")

        # (2) Non-empty list, no alias match and no direct match -> fall through to 1.0.
        fm.score_family(["not_a_real_family_name", "another_miss"], "AlsoMissing")

        # (3) Generic 'sans-serif' alias; first candidate in expanded list matches.
        fm.score_family(["sans-serif"], "DejaVu Sans")

        # (4) Scalar family string coerced to single-element list; direct equality match.
        fm.score_family("DejaVu Sans", "dejavu sans")
