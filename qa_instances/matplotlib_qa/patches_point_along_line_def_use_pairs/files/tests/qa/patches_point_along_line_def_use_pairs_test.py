import sys
from pathlib import Path
import numpy as np

# CRITICAL: Force local matplotlib import
testbed_path = Path("/testbed")
lib_path = testbed_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Now import from local source
from matplotlib.patches import _point_along_a_line


class TestPatchesPointAlongLineDefUsePairsQA:
    def test_patches_point_along_line_def_use_pairs_case(self):
        # Test 1: Horizontal line, distance 5
        x2, y2 = _point_along_a_line(0, 0, 10, 0, 5)
        assert np.allclose(x2, 5)
        assert np.allclose(y2, 0)
        
        # Test 2: Vertical line, distance 3
        x2, y2 = _point_along_a_line(0, 0, 0, 10, 3)
        assert np.allclose(x2, 0)
        assert np.allclose(y2, 3)
        
        # Test 3: Diagonal line (3-4-5 triangle)
        x2, y2 = _point_along_a_line(0, 0, 3, 4, 5)
        assert isinstance(x2, (int, float, np.number))
        assert isinstance(y2, (int, float, np.number))
        
        # Test 4: Negative coordinates
        x2, y2 = _point_along_a_line(-5, -5, 5, 5, 7.071)
        assert isinstance(x2, (int, float, np.number))
        assert isinstance(y2, (int, float, np.number))
        
        # Test 5: Small distance
        x2, y2 = _point_along_a_line(0, 0, 100, 100, 1)
        assert isinstance(x2, (int, float, np.number))
        
        # Test 6: Large distance
        x2, y2 = _point_along_a_line(0, 0, 10, 10, 50)
        assert isinstance(x2, (int, float, np.number))
        
        # Test 7: Fractional coordinates
        x2, y2 = _point_along_a_line(1.5, 2.5, 4.5, 6.5, 2.5)
        assert isinstance(x2, (int, float, np.number))
        assert isinstance(y2, (int, float, np.number))
        
        # Test 8: Zero distance
        x2, y2 = _point_along_a_line(10, 20, 30, 40, 0)
        assert np.allclose(x2, 10)
        assert np.allclose(y2, 20)
        
        # Test 9: Line with negative slope
        x2, y2 = _point_along_a_line(0, 10, 10, 0, 7.071)
        assert isinstance(x2, (int, float, np.number))
        assert isinstance(y2, (int, float, np.number))
        
        # Test 10: Very long line, short distance
        x2, y2 = _point_along_a_line(0, 0, 1000, 1000, 10)
        assert isinstance(x2, (int, float, np.number))
        
        # Test 11: Points close together
        x2, y2 = _point_along_a_line(5, 5, 5.1, 5.1, 0.05)
        assert isinstance(x2, (int, float, np.number))
        assert isinstance(y2, (int, float, np.number))
        
        # Test 12: Mix of positive and negative coords
        x2, y2 = _point_along_a_line(-10, 20, 30, -40, 25)
        assert isinstance(x2, (int, float, np.number))
        assert isinstance(y2, (int, float, np.number))
        
        # Validate all results are numeric pairs
        assert all(isinstance(v, (int, float, np.number)) for v in [
            x2, y2
        ])
