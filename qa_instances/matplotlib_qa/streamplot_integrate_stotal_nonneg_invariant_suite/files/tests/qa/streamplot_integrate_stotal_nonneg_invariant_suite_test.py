import sys
from pathlib import Path
import pytest
import numpy as np

# CRITICAL: Force local matplotlib import
testbed_path = Path("/testbed")
lib_path = testbed_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Now import from local source
from matplotlib.streamplot import _integrate_rk12, Grid, StreamMask, DomainMap


# Generate diverse velocity fields for testing
def make_velocity_field(field_type, grid_size=10):
    """Create different velocity fields for testing."""
    x = np.linspace(0, grid_size-1, grid_size)
    y = np.linspace(0, grid_size-1, grid_size)
    Y, X = np.meshgrid(y, x)
    
    if field_type == 'uniform':
        u = np.ones_like(X, dtype=float)
        v = np.zeros_like(Y, dtype=float)
    elif field_type == 'rotating':
        u = -Y.astype(float)
        v = X.astype(float)
    elif field_type == 'radial':
        u = X.astype(float) - grid_size / 2
        v = Y.astype(float) - grid_size / 2
    elif field_type == 'vortex':
        u = np.sin(X / 2) * np.cos(Y / 2)
        v = -np.cos(X / 2) * np.sin(Y / 2)
    elif field_type == 'diagonal':
        u = np.ones_like(X, dtype=float) * 0.7
        v = np.ones_like(Y, dtype=float) * 0.7
    elif field_type == 'wave':
        u = np.sin(Y)
        v = np.cos(X)
    elif field_type == 'saddle':
        u = X.astype(float)
        v = -Y.astype(float)
    elif field_type == 'spiral':
        r = np.sqrt((X - grid_size/2)**2 + (Y - grid_size/2)**2)
        u = -Y + grid_size/2 + X * 0.1
        v = X - grid_size/2 + Y * 0.1
    elif field_type == 'circular':
        cx, cy = grid_size/2, grid_size/2
        u = -(Y - cy)
        v = (X - cx)
    elif field_type == 'shear':
        u = Y.astype(float) / grid_size
        v = np.zeros_like(Y, dtype=float)
    elif field_type == 'convergent':
        u = -(X - grid_size/2)
        v = -(Y - grid_size/2)
    elif field_type == 'divergent':
        u = (X - grid_size/2)
        v = (Y - grid_size/2)
    elif field_type == 'complex1':
        u = np.sin(X * 0.5) * np.cos(Y * 0.5) + 0.5
        v = np.cos(X * 0.5) * np.sin(Y * 0.5)
    elif field_type == 'complex2':
        u = X / grid_size - Y / grid_size
        v = X / grid_size + Y / grid_size
    elif field_type == 'nonlinear':
        u = X**2 / grid_size**2
        v = Y**2 / grid_size**2
    elif field_type == 'oscillating':
        u = np.sin(X) * np.cos(Y)
        v = np.cos(X) * np.sin(Y)
    elif field_type == 'mixed1':
        u = X * np.sin(Y / 2)
        v = Y * np.cos(X / 2)
    elif field_type == 'mixed2':
        u = (X - grid_size/2) * 0.5 + np.sin(Y)
        v = (Y - grid_size/2) * 0.5 + np.cos(X)
    elif field_type == 'hyperbolic':
        u = X.astype(float)
        v = Y.astype(float)
    elif field_type == 'exponential':
        u = np.exp(-(X - grid_size/2)**2 / 10)
        v = np.exp(-(Y - grid_size/2)**2 / 10)
    elif field_type == 'polynomial':
        u = X**2 / 100 - Y / 10
        v = Y**2 / 100 - X / 10
    elif field_type == 'trigonometric':
        u = np.sin(X / 2) + np.cos(Y / 2)
        v = np.cos(X / 2) - np.sin(Y / 2)
    elif field_type == 'gaussian':
        u = np.exp(-((X-grid_size/2)**2 + (Y-grid_size/2)**2) / 20)
        v = np.exp(-((X-grid_size/2)**2 + (Y-grid_size/2)**2) / 20)
    elif field_type == 'asymmetric':
        u = X / 5 + Y / 10
        v = X / 10 - Y / 5
    else:  # field_type == 'random'
        u = np.random.randn(*X.shape) * 0.5
        v = np.random.randn(*Y.shape) * 0.5
    
    return x, y, u, v


FIELD_TYPES = [
    'uniform', 'rotating', 'radial', 'vortex', 'diagonal', 'wave',
    'saddle', 'spiral', 'circular', 'shear', 'convergent', 'divergent',
    'complex1', 'complex2', 'nonlinear', 'oscillating', 'mixed1', 'mixed2',
    'hyperbolic', 'exponential', 'polynomial', 'trigonometric', 'gaussian', 'asymmetric'
]


class TestStreamplotIntegrateStotalNonnegInvariantSuiteQA:
    @pytest.mark.parametrize("field_type", FIELD_TYPES)
    def test_streamplot_integrate_stotal_nonneg_invariant_suite_case(self, field_type):
        grid_size = 10
        x, y, u, v = make_velocity_field(field_type, grid_size)
        
        grid = Grid(x, y)
        mask = StreamMask(density=1)
        dmap = DomainMap(grid, mask)
        
        def velocity_func(xi, yi):
            from matplotlib.streamplot import interpgrid
            return interpgrid(u, xi, yi), interpgrid(v, xi, yi)
        
        x0, y0 = grid_size / 2, grid_size / 2
        maxlength = 5.0
        
        dmap.start_trajectory(x0, y0)
        stotal, trajectory = _integrate_rk12(x0, y0, dmap, velocity_func, maxlength, True)
        
        assert stotal >= 0
        assert len(trajectory) >= 0
