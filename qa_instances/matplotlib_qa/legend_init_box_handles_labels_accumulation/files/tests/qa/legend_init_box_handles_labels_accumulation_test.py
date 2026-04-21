import sys
from pathlib import Path
import numpy as np

# Force use of local matplotlib source instead of system-installed package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "lib"))

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


class TestLegendInitBoxHandlesLabelsAccumulationQA:
    def test_legend_init_box_handles_labels_accumulation_case(self):
        # Create a figure and axes
        fig, ax = plt.subplots()
        
        # Create some plot elements with labels to generate legend entries
        # We'll create exactly 3 items so we can track the state after 3 iterations
        line1 = ax.plot([0, 1], [0, 1], label='Line 1')[0]
        line2 = ax.plot([0, 1], [1, 0], label='Line 2')[0]
        rect = Rectangle((0.2, 0.2), 0.3, 0.3, label='Rectangle 1')
        ax.add_patch(rect)
        
        # Create a legend, which internally calls _init_legend_box
        # This will iterate through the handles and build handles_and_labels list
        legend = ax.legend()
        
        # Verify legend was created
        assert legend is not None
        assert len(legend.get_texts()) == 3
        
        plt.close(fig)
