import sys
from pathlib import Path
import numpy as np

# CRITICAL: Force local matplotlib import
testbed_path = Path("/testbed")
lib_path = testbed_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Now import from local source
from matplotlib.streamplot import _integrate_rk12, DomainMap, Grid, StreamMask


class TestStreamplotIntegrateRk12DefUsePairsQA:
    def test_streamplot_integrate_rk12_def_use_pairs_case(self):
        # Create simple velocity field for integration
        nx, ny = 10, 10
        x = np.linspace(0, 1, nx)
        y = np.linspace(0, 1, ny)
        grid = Grid(x, y)
        
        def f1(xi, yi):
            if not grid.within_grid(xi, yi):
                from matplotlib.streamplot import OutOfBounds
                raise OutOfBounds
            return (1.0, 1.0)
        
        # Test 1: Simple constant velocity field
        mask1 = StreamMask(density=1)
        dmap1 = DomainMap(grid, mask1)
        dmap1.start_trajectory(0.1, 0.1)
        stotal, traj = _integrate_rk12(0.1, 0.1, dmap1, f1, maxlength=2.0)
        assert stotal >= 0
        assert len(traj) > 0
        
        # Test 2: Zero velocity (should terminate quickly)
        def f2(xi, yi):
            if not grid.within_grid(xi, yi):
                from matplotlib.streamplot import OutOfBounds
                raise OutOfBounds
            from matplotlib.streamplot import TerminateTrajectory
            raise TerminateTrajectory
        
        mask2 = StreamMask(density=1)
        dmap2 = DomainMap(grid, mask2)
        dmap2.start_trajectory(0.5, 0.5)
        stotal, traj = _integrate_rk12(0.5, 0.5, dmap2, f2, maxlength=1.0)
        assert isinstance(stotal, (int, float, np.number))
        
        # Test 3: Velocity that goes out of bounds
        def f3(xi, yi):
            if not grid.within_grid(xi, yi):
                from matplotlib.streamplot import OutOfBounds
                raise OutOfBounds
            return (2.0, 2.0)
        
        mask3 = StreamMask(density=1)
        dmap3 = DomainMap(grid, mask3)
        dmap3.start_trajectory(0.1, 0.1)
        stotal, traj = _integrate_rk12(0.1, 0.1, dmap3, f3, maxlength=1.5)
        assert isinstance(stotal, (int, float, np.number))
        
        # Test 4: Different starting point
        mask4 = StreamMask(density=1)
        dmap4 = DomainMap(grid, mask4)
        dmap4.start_trajectory(0.3, 0.3)
        stotal, traj = _integrate_rk12(0.3, 0.3, dmap4, f1, maxlength=1.0)
        assert stotal >= 0
        
        # Test 5: Small maxlength
        mask5 = StreamMask(density=1)
        dmap5 = DomainMap(grid, mask5)
        dmap5.start_trajectory(0.5, 0.5)
        stotal, traj = _integrate_rk12(0.5, 0.5, dmap5, f1, maxlength=0.1)
        assert stotal <= 0.15
        
        # Test 6: Larger maxlength
        mask6 = StreamMask(density=1)
        dmap6 = DomainMap(grid, mask6)
        dmap6.start_trajectory(0.2, 0.2)
        stotal, traj = _integrate_rk12(0.2, 0.2, dmap6, f1, maxlength=3.0)
        assert isinstance(stotal, (int, float, np.number))
        
        # Test 7: Diagonal velocity
        def f4(xi, yi):
            if not grid.within_grid(xi, yi):
                from matplotlib.streamplot import OutOfBounds
                raise OutOfBounds
            return (0.7, 0.7)
        
        mask7 = StreamMask(density=1)
        dmap7 = DomainMap(grid, mask7)
        dmap7.start_trajectory(0.1, 0.1)
        stotal, traj = _integrate_rk12(0.1, 0.1, dmap7, f4, maxlength=2.0)
        assert len(traj) > 0
        
        # Test 8: Variable velocity field
        def f5(xi, yi):
            if not grid.within_grid(xi, yi):
                from matplotlib.streamplot import OutOfBounds
                raise OutOfBounds
            return (xi, yi)
        
        mask8 = StreamMask(density=1)
        dmap8 = DomainMap(grid, mask8)
        dmap8.start_trajectory(0.3, 0.3)
        stotal, traj = _integrate_rk12(0.3, 0.3, dmap8, f5, maxlength=1.5)
        assert isinstance(stotal, (int, float, np.number))
        
        # Test 9: Edge case - start near boundary
        mask9 = StreamMask(density=1)
        dmap9 = DomainMap(grid, mask9)
        dmap9.start_trajectory(0.95, 0.95)
        stotal, traj = _integrate_rk12(0.95, 0.95, dmap9, f1, maxlength=1.0)
        assert isinstance(stotal, (int, float, np.number))
        
        # Test 10: Multiple trajectory tests
        for i, (x0, y0) in enumerate([(0.1, 0.2), (0.4, 0.5), (0.7, 0.8)]):
            mask_temp = StreamMask(density=1)
            dmap_temp = DomainMap(grid, mask_temp)
            dmap_temp.start_trajectory(x0, y0)
            stotal, traj = _integrate_rk12(x0, y0, dmap_temp, f1, maxlength=1.0)
            assert isinstance(stotal, (int, float, np.number))
            assert isinstance(traj, list)
