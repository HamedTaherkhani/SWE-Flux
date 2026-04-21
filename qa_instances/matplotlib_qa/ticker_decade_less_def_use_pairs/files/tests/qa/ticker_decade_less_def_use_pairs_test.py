import sys
from pathlib import Path
import numpy as np

# CRITICAL: Force local matplotlib import
testbed_path = Path("/testbed")
lib_path = testbed_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Now import from local source
from matplotlib.ticker import _decade_less


class TestTickerDecadeLessDefUsePairsQA:
    def test_ticker_decade_less_def_use_pairs_case(self):
        # Test 1: Positive value, base 10
        result1 = _decade_less(150, 10)
        assert result1 == 100
        
        # Test 2: Exactly a power of base
        result2 = _decade_less(100, 10)
        assert result2 == 10
        
        # Test 3: Small positive value
        result3 = _decade_less(5, 10)
        assert result3 == 1
        
        # Test 4: Negative value
        result4 = _decade_less(-150, 10)
        assert isinstance(result4, (int, float, np.number))
        
        # Test 5: Negative exact power
        result5 = _decade_less(-100, 10)
        assert isinstance(result5, (int, float, np.number))
        
        # Test 6: Base 2
        result6 = _decade_less(10, 2)
        assert result6 == 8
        
        # Test 7: Base 2, exact power
        result7 = _decade_less(16, 2)
        assert result7 == 8
        
        # Test 8: Large value
        result8 = _decade_less(1000, 10)
        assert result8 == 100
        
        # Test 9: Very small positive value
        result9 = _decade_less(0.5, 10)
        assert isinstance(result9, (int, float, np.number))
        
        # Test 10: Fractional base
        result10 = _decade_less(50, 5)
        assert result10 == 25
        
        # Test 11: Between powers
        result11 = _decade_less(250, 10)
        assert result11 == 100
        
        # Test 12: Base 3
        result12 = _decade_less(100, 3)
        assert isinstance(result12, (int, float, np.number))
        
        # Validate all results are numeric
        assert all(isinstance(r, (int, float, np.number)) for r in [
            result1, result2, result3, result4, result5, result6,
            result7, result8, result9, result10, result11, result12
        ])
