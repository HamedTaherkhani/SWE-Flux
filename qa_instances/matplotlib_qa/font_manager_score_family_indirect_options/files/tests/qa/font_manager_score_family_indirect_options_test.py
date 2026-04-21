import sys
from pathlib import Path

# Force use of local matplotlib source instead of system-installed package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "lib"))

from matplotlib.font_manager import FontManager


class TestFontManagerScoreFamilyIndirectOptionsQA:
    def test_font_manager_score_family_indirect_options_case(self):
        # Create a FontManager instance
        fm = FontManager()
        
        # Define the families list with 'serif' alias and other font families
        # 'serif' is a font_family_alias that will trigger the _expand_aliases path
        families = ['serif', 'DejaVu Sans', 'Arial', 'Times New Roman']
        
        # Get a real font name from the font list to test against
        # We'll use the first font in the ttflist as family2
        if len(fm.ttflist) > 0:
            family2 = fm.ttflist[0].name
        else:
            # Fallback if no fonts available
            family2 = 'DejaVu Sans'
        
        # Call score_family directly with the families list
        # This will iterate through families, and when it hits 'serif',
        # it will create the 'options' list at line 1195
        score = fm.score_family(families, family2)
        
        # Verify we got a valid score back (between 0.0 and 1.0)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
