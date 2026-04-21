import sys
from pathlib import Path

MATPLOTLIB_SRC = Path("/testbed/lib")
if str(MATPLOTLIB_SRC) not in sys.path:
    sys.path.insert(0, str(MATPLOTLIB_SRC))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.transforms import Bbox


class TestLegendBboxAnchorOffsetStateDeepQA:
    def test_legend_bbox_anchor_offset_state_deep_case(self):
        np.random.seed(42)
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        x = np.linspace(0, 10, 100)
        y1 = np.sin(x) * np.exp(-x/10) + np.random.normal(0, 0.1, 100)
        y2 = np.cos(x) * np.exp(-x/10) + np.random.normal(0, 0.15, 100)
        y3 = np.sin(2*x) * np.exp(-x/15) + np.random.normal(0, 0.08, 100)
        y4 = np.cos(2*x) * np.exp(-x/15) + np.random.normal(0, 0.12, 100)
        
        line1 = ax.plot(x, y1, 'r-', linewidth=2, label='Damped Sine A')[0]
        line2 = ax.plot(x, y2, 'b--', linewidth=2, label='Damped Cosine A')[0]
        line3 = ax.plot(x, y3, 'g-.', linewidth=2, label='Damped Sine B')[0]
        line4 = ax.plot(x, y4, 'm:', linewidth=2, label='Damped Cosine B')[0]
        
        ax.set_xlabel('Time (s)', fontsize=12)
        ax.set_ylabel('Amplitude', fontsize=12)
        ax.set_title('Multi-Component Signal Analysis', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim(0, 10)
        ax.set_ylim(-1.5, 1.5)
        
        legend = ax.legend(
            loc='upper right',
            bbox_to_anchor=(0.98, 0.95),
            ncol=2,
            frameon=True,
            shadow=True,
            fancybox=True,
            framealpha=0.9,
            fontsize=10,
            title='Signal Components',
            title_fontsize=11
        )
        
        fig.canvas.draw()
        
        legend_bbox = legend.get_window_extent()
        legend_frame = legend.get_frame()
        
        assert legend_bbox.width > 0
        assert legend_bbox.height > 0
        assert legend_frame is not None
        assert len(legend.get_texts()) == 4
        
        plt.close(fig)
