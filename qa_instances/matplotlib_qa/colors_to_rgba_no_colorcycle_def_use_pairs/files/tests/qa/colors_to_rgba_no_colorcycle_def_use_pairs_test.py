import sys
from pathlib import Path

# CRITICAL: Force local matplotlib import
testbed_path = Path("/testbed")
lib_path = testbed_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Now import from local source
from matplotlib.colors import _to_rgba_no_colorcycle


class TestColorsToRgbaNoColorcycleDefUsePairsQA:
    def test_colors_to_rgba_no_colorcycle_def_use_pairs_case(self):
        # Test 1: Named color lookup with fallback
        result1 = _to_rgba_no_colorcycle('red')
        assert len(result1) == 4
        
        # Test 2: Named color lowercase fallback
        result2 = _to_rgba_no_colorcycle('Red')
        assert len(result2) == 4
        
        # Test 3: Hex color #rrggbb format with alpha override
        result3 = _to_rgba_no_colorcycle('#FF5733', alpha=0.5)
        assert result3[3] == 0.5
        
        # Test 4: Hex color #rgb shorthand
        result4 = _to_rgba_no_colorcycle('#F57')
        assert len(result4) == 4
        
        # Test 5: Hex color #rrggbbaa format
        result5 = _to_rgba_no_colorcycle('#FF5733AA')
        assert len(result5) == 4
        
        # Test 6: Hex color #rgba shorthand with alpha override
        result6 = _to_rgba_no_colorcycle('#F57A', alpha=0.3)
        assert result6[3] == 0.3
        
        # Test 7: String gray value
        result7 = _to_rgba_no_colorcycle('0.7')
        assert result7[0] == 0.7
        
        # Test 8: Tuple RGB
        result8 = _to_rgba_no_colorcycle((0.1, 0.2, 0.3))
        assert len(result8) == 4
        
        # Test 9: Tuple RGBA with alpha override
        result9 = _to_rgba_no_colorcycle((0.1, 0.2, 0.3, 0.9), alpha=0.6)
        assert result9[3] == 0.6
        
        # Test 10: Another named color to exercise cache behavior
        result10 = _to_rgba_no_colorcycle('blue', alpha=0.8)
        assert result10[3] == 0.8
        
        # Test 11: Complex named color (tableau color)
        result11 = _to_rgba_no_colorcycle('tab:blue')
        assert len(result11) == 4
        
        # Validate results
        assert isinstance(result1, tuple)
        assert isinstance(result2, tuple)
        assert isinstance(result3, tuple)
        assert isinstance(result4, tuple)
        assert isinstance(result5, tuple)
        assert isinstance(result6, tuple)
        assert isinstance(result7, tuple)
        assert isinstance(result8, tuple)
        assert isinstance(result9, tuple)
        assert isinstance(result10, tuple)
        assert isinstance(result11, tuple)
