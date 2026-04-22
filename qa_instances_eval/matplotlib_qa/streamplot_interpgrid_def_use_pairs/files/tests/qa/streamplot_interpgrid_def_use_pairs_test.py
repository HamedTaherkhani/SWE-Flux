import sys
from pathlib import Path
import numpy as np

# CRITICAL: Force local matplotlib import
testbed_path = Path("/testbed")
lib_path = testbed_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Now import from local source
from matplotlib.streamplot import interpgrid


class TestStreamplotInterpgridDefUsePairsQA:
    def test_streamplot_interpgrid_def_use_pairs_case(self):
        # Test 1: Array input - basic interpolation
        a = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
        xi = np.array([0.5, 1.5])
        yi = np.array([0.5, 1.5])
        result = interpgrid(a, xi, yi)
        assert result.shape == (2,)
        
        # Test 2: Scalar input - basic interpolation
        a = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
        result = interpgrid(a, 0.5, 0.5)
        assert isinstance(result, (float, np.floating))
        
        # Test 3: Scalar input at boundary x (Nx-1)
        a = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
        result = interpgrid(a, 2.0, 0.5)  # x = 2 == Nx-1
        assert isinstance(result, (float, np.floating))
        
        # Test 4: Scalar input at boundary y (Ny-1)
        a = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
        result = interpgrid(a, 0.5, 2.0)  # y = 2 == Ny-1
        assert isinstance(result, (float, np.floating))
        
        # Test 5: Scalar input at both boundaries
        a = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
        result = interpgrid(a, 2.0, 2.0)  # x = 2, y = 2 (both at max)
        assert np.allclose(result, 9.0)
        
        # Test 6: Array input with multiple points
        a = np.array([[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0], [9.0, 10.0, 11.0, 12.0], [13.0, 14.0, 15.0, 16.0]])
        xi = np.array([0.25, 1.25, 2.25])
        yi = np.array([0.25, 1.25, 2.25])
        result = interpgrid(a, xi, yi)
        assert result.shape == (3,)
        
        # Test 7: Scalar input at corner (0,0)
        a = np.array([[10.0, 20.0], [30.0, 40.0]])
        result = interpgrid(a, 0.0, 0.0)
        assert np.allclose(result, 10.0)
        
        # Test 8: Array input near boundary
        a = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
        xi = np.array([1.9, 1.5])
        yi = np.array([1.9, 1.5])
        result = interpgrid(a, xi, yi)
        assert result.shape == (2,)
        
        # Test 9: Scalar fractional interpolation
        a = np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0], [6.0, 7.0, 8.0]])
        result = interpgrid(a, 1.0, 1.0)
        assert np.allclose(result, 4.0)
        
        # Test 10: Array input with zeros
        a = np.zeros((5, 5))
        a[2, 2] = 10.0
        xi = np.array([1.5, 2.5])
        yi = np.array([1.5, 2.5])
        result = interpgrid(a, xi, yi)
        assert result.shape == (2,)
        
        # Test 11: Scalar input with negative values
        a = np.array([[-1.0, -2.0], [-3.0, -4.0]])
        result = interpgrid(a, 0.5, 0.5)
        assert result < 0
        
        # Test 12: Large array with multiple array inputs
        a = np.random.rand(10, 10)
        xi = np.array([2.5, 5.5, 7.5])
        yi = np.array([3.5, 6.5, 8.5])
        result = interpgrid(a, xi, yi)
        assert result.shape == (3,)
