import sys
from pathlib import Path
import numpy as np

# CRITICAL: Force local matplotlib import
testbed_path = Path("/testbed")
lib_path = testbed_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Now import from local source
from matplotlib.contour import _find_closest_point_on_path


class TestContourFindClosestPointOnPathDefUsePairsQA:
    def test_contour_find_closest_point_on_path_def_use_pairs_case(self):
        # Test 1: Single point (special case)
        xys1 = np.array([[1.0, 2.0]])
        p1 = np.array([3.0, 4.0])
        d2, proj, leg = _find_closest_point_on_path(xys1, p1)
        assert leg == (0, 0)
        assert np.allclose(proj, [1.0, 2.0])
        
        # Test 2: Simple line segment - closest point at vertex
        xys2 = np.array([[0.0, 0.0], [1.0, 0.0]])
        p2 = np.array([0.1, 0.5])
        d2, proj, leg = _find_closest_point_on_path(xys2, p2)
        assert isinstance(d2, (float, np.floating))
        assert len(proj) == 2
        assert len(leg) == 2
        
        # Test 3: Simple line segment - closest point in middle
        xys3 = np.array([[0.0, 0.0], [10.0, 0.0]])
        p3 = np.array([5.0, 3.0])
        d2, proj, leg = _find_closest_point_on_path(xys3, p3)
        assert np.allclose(proj[0], 5.0)
        
        # Test 4: Multi-segment path
        xys4 = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
        p4 = np.array([0.5, 0.5])
        d2, proj, leg = _find_closest_point_on_path(xys4, p4)
        assert leg[0] >= 0 and leg[1] <= 3
        
        # Test 5: Path with zero-length segment (edge case)
        xys5 = np.array([[0.0, 0.0], [0.0, 0.0], [1.0, 1.0]])
        p5 = np.array([0.5, 0.5])
        d2, proj, leg = _find_closest_point_on_path(xys5, p5)
        assert isinstance(d2, (float, np.floating))
        
        # Test 6: Point very far from path
        xys6 = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
        p6 = np.array([1.0, 100.0])
        d2, proj, leg = _find_closest_point_on_path(xys6, p6)
        assert d2 > 9000  # Should be very large
        
        # Test 7: Point on path segment
        xys7 = np.array([[0.0, 0.0], [10.0, 10.0]])
        p7 = np.array([5.0, 5.0])
        d2, proj, leg = _find_closest_point_on_path(xys7, p7)
        assert d2 < 0.01  # Very close to path
        
        # Test 8: Complex path with many segments
        xys8 = np.array([
            [0.0, 0.0], [1.0, 1.0], [2.0, 0.0],
            [3.0, 1.0], [4.0, 0.0], [5.0, 1.0]
        ])
        p8 = np.array([2.5, 1.5])
        d2, proj, leg = _find_closest_point_on_path(xys8, p8)
        assert leg[1] - leg[0] == 1  # Consecutive indices
        
        # Test 9: Projection beyond segment endpoints (clipped to [0, 1])
        xys9 = np.array([[0.0, 0.0], [1.0, 0.0]])
        p9 = np.array([2.0, 1.0])
        d2, proj, leg = _find_closest_point_on_path(xys9, p9)
        # Should project to (1.0, 0.0), the end of the segment
        assert proj[0] <= 1.0
        
        # Test 10: Negative coordinates
        xys10 = np.array([[-5.0, -3.0], [-2.0, -1.0], [0.0, 0.0]])
        p10 = np.array([-3.5, -2.5])
        d2, proj, leg = _find_closest_point_on_path(xys10, p10)
        assert isinstance(d2, (float, np.floating))
        assert len(leg) == 2
        
        # Validate all results have correct structure
        assert all(isinstance(proj, np.ndarray) for d2, proj, leg in [
            _find_closest_point_on_path(xys1, p1),
            _find_closest_point_on_path(xys2, p2),
            _find_closest_point_on_path(xys3, p3),
        ])
