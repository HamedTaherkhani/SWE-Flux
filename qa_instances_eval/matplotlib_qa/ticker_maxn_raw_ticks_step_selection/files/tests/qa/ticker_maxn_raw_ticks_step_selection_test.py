import sys
from pathlib import Path
import numpy as np

# Force use of local matplotlib source instead of system-installed package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "lib"))

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


class TestTickerMaxNRawTicksStepSelectionQA:
    def test_ticker_maxn_raw_ticks_step_selection_case(self):
        # Create a MaxNLocator with specific configuration
        # nbins=4 will create a scenario where step selection logic is triggered
        locator = MaxNLocator(nbins=4, steps=[1, 2, 5, 10])
        
        # Set up an axis context (needed for the locator to work)
        fig, ax = plt.subplots()
        ax.set_xlim(0, 100)
        locator.set_axis(ax.xaxis)
        
        # Call _raw_ticks which will execute the complex step selection loop
        # This will trigger the loop at line 2203 that iterates through steps
        # and calculates ticks for each step until min_n_ticks is satisfied
        vmin, vmax = 12.3, 87.6
        ticks = locator._raw_ticks(vmin, vmax)
        
        # Verify ticks were generated
        assert ticks is not None
        assert len(ticks) > 0
        assert isinstance(ticks, np.ndarray)
        
        plt.close(fig)
