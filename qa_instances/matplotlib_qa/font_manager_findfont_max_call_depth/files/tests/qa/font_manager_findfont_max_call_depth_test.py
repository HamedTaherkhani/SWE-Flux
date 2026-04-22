#!/usr/bin/env python3
"""
Complex font matching test that triggers deep call stacks through
recursive font manager lookups with multiple fallback families.
"""
import sys
from pathlib import Path

# Force local source import - test file is at /testbed/tests/qa/xxx_test.py
# So we need to go up 2 levels to /testbed, then add /lib
testbed_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(testbed_root / "lib"))

import matplotlib.font_manager as fm
from matplotlib.font_manager import FontProperties


class TestFontManagerFindfontMaxCallDepthQA:
    def test_font_manager_findfont_max_call_depth_case(self):
        """
        Test complex font matching with multiple generic families, styles, and weights.
        This creates a complex execution path with deep call stacks involving:
        1. Multiple font family lookups with fallbacks
        2. Generic family expansions (sans-serif, serif, monospace, etc.)
        3. Repeated score_family, score_weight, score_style calls
        4. Cache lookups and property expansions
        """
        # Create a font properties object with multiple generic families
        # This will trigger expansion and scoring for each family
        prop1 = FontProperties(
            family=['sans-serif', 'serif', 'monospace', 'cursive', 'fantasy'],
            weight='bold',
            style='italic',
            variant='normal',
            stretch='expanded',
            size=12
        )
        
        # First findfont call - triggers deep call stack with multiple families
        font1 = fm.findfont(prop1, fallback_to_default=True)
        
        # Second call with different properties to increase complexity
        prop2 = FontProperties(
            family=['monospace', 'sans-serif', 'serif'],
            weight=700,
            style='oblique',
            stretch='semi-condensed',
            size=14
        )
        
        font2 = fm.findfont(prop2, fallback_to_default=True)
        
        # Third call with numeric weights and specific family order
        prop3 = FontProperties(
            family=['fantasy', 'cursive', 'monospace', 'serif', 'sans-serif'],
            weight=600,
            style='normal',
            stretch='condensed',
            size='large'
        )
        
        font3 = fm.findfont(prop3, fallback_to_default=True)
        
        # Verify we got valid fonts
        assert font1 is not None and Path(font1).exists()
        assert font2 is not None and Path(font2).exists()
        assert font3 is not None and Path(font3).exists()
