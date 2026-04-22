import sys
from pathlib import Path
import numpy as np

# CRITICAL: Force local matplotlib import
testbed_path = Path("/testbed")
lib_path = testbed_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Now import from local source
from matplotlib.colors import _create_lookup_table


class TestColorsCreateLookupTableDefUsePairsQA:
    def test_colors_create_lookup_table_def_use_pairs_case(self):
        # Test 1: Callable data with default gamma
        def linear_func(x):
            return x
        result1 = _create_lookup_table(10, linear_func)
        assert len(result1) == 10
        assert result1[0] == 0.0
        assert result1[-1] == 1.0
        
        # Test 2: Callable data with gamma correction
        def square_func(x):
            return x ** 2
        result2 = _create_lookup_table(20, square_func, gamma=2.0)
        assert len(result2) == 20
        
        # Test 3: Array data - simple linear ramp
        data3 = np.array([[0.0, 0.0, 0.0],
                          [0.5, 0.5, 0.5],
                          [1.0, 1.0, 1.0]])
        result3 = _create_lookup_table(15, data3)
        assert len(result3) == 15
        
        # Test 4: Array data with discontinuity (y0 != y1)
        data4 = np.array([[0.0, 0.0, 1.0],
                          [0.3, 0.5, 0.8],
                          [0.7, 0.2, 0.6],
                          [1.0, 1.0, 0.0]])
        result4 = _create_lookup_table(25, data4)
        assert len(result4) == 25
        
        # Test 5: N=1 case (special case)
        data5 = np.array([[0.0, 0.2, 0.3],
                          [0.5, 0.5, 0.6],
                          [1.0, 0.8, 0.9]])
        result5 = _create_lookup_table(1, data5)
        assert result5.shape == ()  # scalar
        assert result5 == 0.8  # y0[-1]
        
        # Test 6: Array data with gamma correction
        data6 = np.array([[0.0, 0.0, 0.0],
                          [0.25, 0.25, 0.25],
                          [0.75, 0.75, 0.75],
                          [1.0, 1.0, 1.0]])
        result6 = _create_lookup_table(30, data6, gamma=0.5)
        assert len(result6) == 30
        
        # Test 7: Sawtooth pattern
        data7 = np.array([[0.0, 1.0, 0.0],
                          [0.2, 1.0, 0.0],
                          [0.4, 1.0, 0.0],
                          [0.6, 1.0, 0.0],
                          [0.8, 1.0, 0.0],
                          [1.0, 1.0, 0.0]])
        result7 = _create_lookup_table(50, data7)
        assert len(result7) == 50
        
        # Test 8: Large N value
        data8 = np.array([[0.0, 0.0, 0.0],
                          [1.0, 1.0, 1.0]])
        result8 = _create_lookup_table(100, data8)
        assert len(result8) == 100
        
        # Test 9: Callable with clipping behavior
        def overflow_func(x):
            return x * 1.5  # Will be clipped to [0, 1]
        result9 = _create_lookup_table(12, overflow_func)
        assert len(result9) == 12
        assert all(result9 <= 1.0)
        
        # Test 10: Complex gamma with callable
        def cubic_func(x):
            return x ** 3
        result10 = _create_lookup_table(18, cubic_func, gamma=3.0)
        assert len(result10) == 18
        
        # Validate all results are numpy arrays or scalars
        assert isinstance(result1, np.ndarray)
        assert isinstance(result2, np.ndarray)
        assert isinstance(result3, np.ndarray)
        assert isinstance(result4, np.ndarray)
        assert isinstance(result5, (np.ndarray, np.generic))
        assert isinstance(result6, np.ndarray)
        assert isinstance(result7, np.ndarray)
        assert isinstance(result8, np.ndarray)
        assert isinstance(result9, np.ndarray)
        assert isinstance(result10, np.ndarray)
        
        # Validate clipping works (all values in [0, 1])
        for result in [result1, result2, result3, result4, result6, result7, result8, result9, result10]:
            assert np.all(result >= 0.0)
            assert np.all(result <= 1.0)
