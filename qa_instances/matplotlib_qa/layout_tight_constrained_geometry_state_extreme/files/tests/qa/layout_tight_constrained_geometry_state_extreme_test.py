import sys
from pathlib import Path

MATPLOTLIB_SRC = Path("/testbed/lib")
if str(MATPLOTLIB_SRC) not in sys.path:
    sys.path.insert(0, str(MATPLOTLIB_SRC))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec


class TestLayoutTightConstrainedGeometryStateExtremeQA:
    def test_layout_tight_constrained_geometry_state_extreme_case(self):
        np.random.seed(123)
        
        fig = plt.figure(figsize=(12, 10))
        
        gs = GridSpec(3, 3, figure=fig, 
                      hspace=0.3, wspace=0.4,
                      left=0.1, right=0.95, 
                      top=0.92, bottom=0.08)
        
        axes = []
        for i in range(3):
            for j in range(3):
                ax = fig.add_subplot(gs[i, j])
                axes.append(ax)
                
                x = np.linspace(0, 10, 50)
                y = np.sin(x + i * j) + np.random.randn(50) * 0.1
                
                ax.plot(x, y, 'o-', label=f'Data {i},{j}')
                ax.set_xlabel(f'X-axis subplot ({i},{j})', fontsize=9)
                ax.set_ylabel(f'Y-axis subplot ({i},{j})', fontsize=9)
                ax.set_title(f'Complex Plot [{i},{j}]', fontsize=10, pad=8)
                ax.legend(loc='upper right', fontsize=7)
                ax.grid(True, alpha=0.3)
        
        fig.suptitle('Multi-Subplot Figure with Complex Layout', 
                     fontsize=14, y=0.98)
        
        renderer = fig.canvas.get_renderer()
        
        tight_bbox_raw = fig.get_tightbbox(renderer)
        
        fig.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        tight_bbox_after = fig.get_tightbbox(renderer)
        
        assert tight_bbox_raw is not None
        assert tight_bbox_after is not None
        assert len(axes) == 9
        
        for ax in axes:
            pos = ax.get_position()
            assert pos.width > 0
            assert pos.height > 0
        
        plt.close(fig)
