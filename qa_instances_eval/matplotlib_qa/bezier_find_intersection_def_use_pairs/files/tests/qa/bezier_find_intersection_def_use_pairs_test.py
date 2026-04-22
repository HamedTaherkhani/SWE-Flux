import sys
from pathlib import Path
import numpy as np

# CRITICAL: Force local matplotlib import
testbed_path = Path("/testbed")
lib_path = testbed_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Now import from local source
from matplotlib.bezier import find_bezier_t_intersecting_with_closedpath


class TestBezierFindIntersectionDefUsePairsQA:
    def test_bezier_find_intersection_def_use_pairs_case(self):
        # Test 1: Simple linear bezier from inside to outside circle
        def bezier1(t):
            return (t * 1.0, 0)  # Line from (0, 0) [inside] to (1, 0) [outside]
        
        def inside_circle(point):
            return point[0]**2 + point[1]**2 < 0.5**2
        
        t0_result, t1_result = find_bezier_t_intersecting_with_closedpath(
            bezier1, inside_circle, t0=0.0, t1=1.0, tolerance=0.01
        )
        assert 0.0 <= t0_result <= 1.0
        assert 0.0 <= t1_result <= 1.0
        
        # Test 2: Vertical bezier
        def bezier2(t):
            return (0, t * 1.0)
        
        t0_result, t1_result = find_bezier_t_intersecting_with_closedpath(
            bezier2, inside_circle, t0=0.0, t1=1.0, tolerance=0.01
        )
        assert isinstance(t0_result, (int, float, np.number))
        assert isinstance(t1_result, (int, float, np.number))
        
        # Test 3: Diagonal bezier
        def bezier3(t):
            return (t * 0.8, t * 0.8)
        
        t0_result, t1_result = find_bezier_t_intersecting_with_closedpath(
            bezier3, inside_circle, t0=0.0, t1=1.0, tolerance=0.01
        )
        assert isinstance(t0_result, (int, float, np.number))
        
        # Test 4: Tight tolerance
        t0_result, t1_result = find_bezier_t_intersecting_with_closedpath(
            bezier1, inside_circle, t0=0.0, t1=1.0, tolerance=0.001
        )
        assert abs(t1_result - t0_result) <= 0.01
        
        # Test 5: Loose tolerance
        t0_result, t1_result = find_bezier_t_intersecting_with_closedpath(
            bezier1, inside_circle, t0=0.0, t1=1.0, tolerance=0.1
        )
        assert isinstance(t0_result, (int, float, np.number))
        
        # Test 6: Smaller circle
        def inside_small_circle(point):
            return point[0]**2 + point[1]**2 < 0.3**2
        
        t0_result, t1_result = find_bezier_t_intersecting_with_closedpath(
            bezier1, inside_small_circle, t0=0.0, t1=1.0, tolerance=0.01
        )
        assert isinstance(t0_result, (int, float, np.number))
        
        # Test 7: Different bezier
        def bezier4(t):
            return (t * 1.2, 0)
        
        t0_result, t1_result = find_bezier_t_intersecting_with_closedpath(
            bezier4, inside_circle, t0=0.0, t1=1.0, tolerance=0.01
        )
        assert 0.0 <= t0_result <= 1.0
        
        # Test 8: Quadratic bezier curve
        def bezier_quad(t):
            x = (1-t)**2 * 0 + 2*(1-t)*t * 0.5 + t**2 * 1.0
            y = (1-t)**2 * 0 + 2*(1-t)*t * 0.5 + t**2 * 0
            return (x, y)
        
        t0_result, t1_result = find_bezier_t_intersecting_with_closedpath(
            bezier_quad, inside_circle, t0=0.0, t1=1.0, tolerance=0.01
        )
        assert isinstance(t0_result, (int, float, np.number))
        
        # Test 9: Another diagonal
        def bezier5(t):
            return (t * 0.6, -t * 0.6)
        
        t0_result, t1_result = find_bezier_t_intersecting_with_closedpath(
            bezier5, inside_circle, t0=0.0, t1=1.0, tolerance=0.01
        )
        assert isinstance(t0_result, (int, float, np.number))
        
        # Test 10: Very tight tolerance (more loop iterations)
        t0_result, t1_result = find_bezier_t_intersecting_with_closedpath(
            bezier1, inside_circle, t0=0.0, t1=1.0, tolerance=0.0001
        )
        assert abs(t1_result - t0_result) <= 0.001
        
        # Validate all pairs of results
        results = [
            find_bezier_t_intersecting_with_closedpath(bezier1, inside_circle, 0.0, 1.0, 0.01),
            find_bezier_t_intersecting_with_closedpath(bezier2, inside_circle, 0.0, 1.0, 0.01),
            find_bezier_t_intersecting_with_closedpath(bezier3, inside_circle, 0.0, 1.0, 0.01),
        ]
        assert all(isinstance(r[0], (int, float, np.number)) and 
                   isinstance(r[1], (int, float, np.number)) for r in results)
