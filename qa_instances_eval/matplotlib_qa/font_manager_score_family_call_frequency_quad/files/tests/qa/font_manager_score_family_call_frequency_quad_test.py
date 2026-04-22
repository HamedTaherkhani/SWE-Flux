#!/usr/bin/env python3
"""
Quad findfont scenario: generic family expansion, weight/style/stretch interaction,
and repeated font-list scoring (score_family) with cache effects across calls.
"""
import sys
from pathlib import Path

# Load Matplotlib from the repo's lib/ tree (not site-packages).
_testbed_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_testbed_root / "lib"))

import importlib

_fm = importlib.import_module("matplotlib.font_manager")
FontProperties = _fm.FontProperties
findfont = _fm.findfont


class TestFontManagerScoreFamilyCallFrequencyQuadQA:
    def test_font_manager_score_family_call_frequency_quad_case(self):
        """
        Four findfont resolutions with overlapping and distinct FontProperties.
        Each call walks the font list with generic family expansion, triggering
        deep score_family use; later calls interact with the FontManager cache.
        """
        prop1 = FontProperties(
            family=["sans-serif", "serif", "monospace", "cursive", "fantasy"],
            weight="bold",
            style="italic",
            stretch="expanded",
            size=12,
        )
        font1 = findfont(prop1, fallback_to_default=True)

        prop2 = FontProperties(
            family=["monospace", "sans-serif"],
            weight=700,
            style="oblique",
            stretch="semi-condensed",
            size=14,
        )
        font2 = findfont(prop2, fallback_to_default=True)

        prop3 = FontProperties(
            family=["fantasy", "serif", "DejaVu Sans"],
            weight=600,
            style="normal",
            stretch="condensed",
            size="large",
        )
        font3 = findfont(prop3, fallback_to_default=True)

        prop4 = FontProperties(family="serif", weight="normal", style="normal")
        font4 = findfont(prop4, fallback_to_default=True)

        assert font1 and Path(font1).exists()
        assert font2 and Path(font2).exists()
        assert font3 and Path(font3).exists()
        assert font4 and Path(font4).exists()
