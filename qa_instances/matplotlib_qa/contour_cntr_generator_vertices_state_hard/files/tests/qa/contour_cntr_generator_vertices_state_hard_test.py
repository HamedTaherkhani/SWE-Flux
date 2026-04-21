import sys
from pathlib import Path

MATPLOTLIB_SRC = Path("/testbed/lib")
if str(MATPLOTLIB_SRC) not in sys.path:
    sys.path.insert(0, str(MATPLOTLIB_SRC))

import numpy as np
import matplotlib.pyplot as plt


class TestContourCntrGeneratorVerticesStateHardQA:
    def test_contour_cntr_generator_vertices_state_hard_case(self):
        np.random.seed(42)
        
        x = np.linspace(-3.0, 3.0, 25)
        y = np.linspace(-2.5, 2.5, 20)
        X, Y = np.meshgrid(x, y)
        
        Z = (np.sin(X) * np.cos(Y) + 
             0.3 * np.sin(2*X) * np.cos(3*Y) + 
             0.1 * X**2 - 0.05 * Y**2 +
             0.02 * np.random.randn(*X.shape))
        
        levels = np.linspace(Z.min(), Z.max(), 8)
        
        fig, ax = plt.subplots()
        contour_set = ax.contour(X, Y, Z, levels=levels)

        # Matplotlib 3.8+: QuadContourSet subclasses Collection directly and has no
        # .collections list; paths live on the ContourSet itself.
        if hasattr(contour_set, "collections") and contour_set.collections:
            assert len(contour_set.collections) > 0
            for collection in contour_set.collections:
                paths = collection.get_paths()
                assert len(paths) >= 0
        else:
            paths = contour_set.get_paths()
            assert len(paths) > 0

        cntr_obj = contour_set._contour_generator
        assert cntr_obj is not None
        
        test_level = float(levels[4])
        vertices_list, codes_list = cntr_obj.create_contour(test_level)
        
        assert isinstance(vertices_list, list)
        assert isinstance(codes_list, list)
        assert len(vertices_list) == len(codes_list)
        
        if len(vertices_list) > 0:
            first_vertices = vertices_list[0]
            assert isinstance(first_vertices, np.ndarray)
            assert first_vertices.ndim == 2
            assert first_vertices.shape[1] == 2
        
        plt.close(fig)
