import sys
from pathlib import Path
import numpy as np

# CRITICAL: Force local matplotlib import
testbed_path = Path("/testbed")
lib_path = testbed_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Now import from local source
from matplotlib.cbook import boxplot_stats


class TestCbookBoxplotStatsDefUsePairsQA:
    def test_cbook_boxplot_stats_def_use_pairs_case(self):
        # Test 1: Simple dataset
        X1 = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]
        result = boxplot_stats(X1)
        assert len(result) == 1
        assert 'mean' in result[0]
        assert 'med' in result[0]
        
        # Test 2: Multiple columns
        X2 = [[1, 2, 3, 4, 5], [10, 20, 30, 40, 50]]
        result = boxplot_stats(X2)
        assert len(result) == 2
        
        # Test 3: With labels
        X3 = [[5, 7, 9, 11], [2, 4, 6, 8]]
        labels = ['A', 'B']
        result = boxplot_stats(X3, labels=labels)
        assert result[0]['label'] == 'A'
        assert result[1]['label'] == 'B'
        
        # Test 4: Different whis value
        X4 = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100]]  # with outlier
        result = boxplot_stats(X4, whis=1.5)
        assert 'fliers' in result[0]
        assert len(result[0]['fliers']) > 0
        
        # Test 5: Percentile-based whis
        X5 = [[10, 20, 30, 40, 50, 60, 70, 80, 90]]
        result = boxplot_stats(X5, whis=(10, 90))
        assert isinstance(result[0]['whislo'], (int, float, np.number))
        
        # Test 6: With bootstrap
        X6 = [[5, 10, 15, 20, 25, 30, 35]]
        result = boxplot_stats(X6, bootstrap=100)
        assert 'cilo' in result[0]
        assert 'cihi' in result[0]
        
        # Test 7: Empty dataset
        X7 = [[]]
        result = boxplot_stats(X7)
        assert np.isnan(result[0]['mean'])
        
        # Test 8: Autorange test (Q1 == Q3)
        X8 = [[5, 5, 5, 5, 5]]
        result = boxplot_stats(X8, autorange=True)
        assert isinstance(result[0]['iqr'], (int, float, np.number))
        
        # Test 9: Large dataset
        X9 = [np.random.randn(100)]
        result = boxplot_stats(X9)
        assert 'q1' in result[0]
        assert 'q3' in result[0]
        
        # Test 10: Multiple columns with different characteristics
        X10 = [
            [1, 2, 3, 4, 5],
            [10, 15, 20, 25, 30],
            [100, 200, 300, 400, 500]
        ]
        result = boxplot_stats(X10)
        assert len(result) == 3
        for stat in result:
            assert 'mean' in stat
            assert 'iqr' in stat
