import sys
from pathlib import Path

MATPLOTLIB_SRC = Path("/testbed/lib")
if str(MATPLOTLIB_SRC) not in sys.path:
    sys.path.insert(0, str(MATPLOTLIB_SRC))

import numpy as np
from matplotlib.colors import LogNorm


class TestColorsNormalizeLogNormVminStateQA:
    def test_colors_normalize_lognorm_vmin_state_case(self):
        data = np.array([
            [0.001, 0.01, 0.1, 1.0],
            [0.005, 0.05, 0.5, 5.0],
            [0.002, 0.02, 0.2, 2.0],
            [0.008, 0.08, 0.8, 8.0]
        ])
        
        norm = LogNorm()
        
        norm.autoscale(data)
        
        normalized_data = norm(data)
        
        assert normalized_data.shape == data.shape
        assert np.all((normalized_data >= 0) & (normalized_data <= 1))
        assert norm.vmin is not None
        assert norm.vmax is not None
        assert norm.vmin < norm.vmax
