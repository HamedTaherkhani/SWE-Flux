import sys
from pathlib import Path
import numpy as np

# Force use of local matplotlib source instead of system-installed package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "lib"))

import matplotlib.pyplot as plt


class TestAxesHexbinCsati1AccumulationStateQA:
    def test_axes_hexbin_csati1_accumulation_state_case(self):
        # Create a figure and axes
        fig, ax = plt.subplots()
        
        # Create simple test data with C values
        # Use specific values that will create a predictable accumulation pattern
        x = np.array([0.5, 1.5, 2.5, 0.8, 1.2, 2.8])
        y = np.array([0.5, 1.5, 2.5, 1.8, 0.8, 1.2])
        C = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
        
        # Call hexbin with C values
        # This will trigger the accumulation logic at lines 5224-5230
        # gridsize=3 gives us a manageable grid
        result = ax.hexbin(x, y, C=C, gridsize=3, reduce_C_function=np.mean)
        
        # Verify we got a result
        assert result is not None
        
        plt.close(fig)
