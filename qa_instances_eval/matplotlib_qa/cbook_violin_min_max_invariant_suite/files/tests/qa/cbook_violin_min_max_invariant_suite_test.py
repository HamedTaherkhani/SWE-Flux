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
from matplotlib.cbook import violin_stats


# Create a simple method for violin plots (just returns uniform values)
def simple_method(data, coords):
    """Simple method that returns constant values based on data mean."""
    mean = np.mean(data)
    # Return array of same length as coords with values near the mean
    return np.ones(len(coords)) * (1.0 / (np.std(data) + 0.1))


# Generate diverse test datasets for violin_stats
def make_test_data(data_type):
    """Create different distributions for testing."""
    np.random.seed(hash(data_type) % (2**32))
    
    if data_type == 'normal':
        return [np.random.randn(50)]
    elif data_type == 'uniform':
        return [np.random.uniform(-10, 10, 50)]
    elif data_type == 'exponential':
        return [np.random.exponential(2.0, 50)]
    elif data_type == 'bimodal':
        return [np.concatenate([np.random.randn(25), np.random.randn(25) + 5])]
    elif data_type == 'skewed':
        return [np.random.gamma(2, 2, 50)]
    elif data_type == 'heavy_tails':
        return [np.random.standard_t(3, 50)]
    elif data_type == 'constant':
        return [np.ones(50) * 5.0]
    elif data_type == 'with_outliers':
        data = np.random.randn(50)
        data[::10] = np.random.uniform(-20, 20, 5)
        return [data]
    elif data_type == 'small_range':
        return [np.random.uniform(4.9, 5.1, 50)]
    elif data_type == 'large_range':
        return [np.random.uniform(-1000, 1000, 50)]
    elif data_type == 'positive_only':
        return [np.abs(np.random.randn(50)) + 1]
    elif data_type == 'negative_only':
        return [-np.abs(np.random.randn(50)) - 1]
    elif data_type == 'two_columns':
        return [np.random.randn(50), np.random.uniform(0, 10, 50)]
    elif data_type == 'triangular':
        return [np.random.triangular(-5, 0, 5, 50)]
    elif data_type == 'beta':
        return [np.random.beta(2, 5, 50) * 10]
    elif data_type == 'lognormal':
        return [np.random.lognormal(0, 1, 50)]
    elif data_type == 'chi_square':
        return [np.random.chisquare(5, 50)]
    elif data_type == 'laplace':
        return [np.random.laplace(0, 2, 50)]
    elif data_type == 'logistic':
        return [np.random.logistic(0, 2, 50)]
    elif data_type == 'small_sample':
        return [np.array([1.0, 2.0, 3.0, 4.0, 5.0])]
    elif data_type == 'large_sample':
        return [np.random.randn(500)]
    elif data_type == 'integer_like':
        return [np.round(np.random.randn(50) * 10)]
    elif data_type == 'mixed_variance':
        part1 = np.random.randn(25) * 0.1
        part2 = np.random.randn(25) * 5.0
        return [np.concatenate([part1, part2])]
    else:  # 'three_columns'
        return [np.random.randn(50), np.random.exponential(1, 50), np.random.uniform(-5, 5, 50)]


TEST_DATA_TYPES = [
    'normal', 'uniform', 'exponential', 'bimodal', 'skewed', 'heavy_tails',
    'constant', 'with_outliers', 'small_range', 'large_range',
    'positive_only', 'negative_only', 'two_columns', 'triangular',
    'beta', 'lognormal', 'chi_square', 'laplace', 'logistic',
    'small_sample', 'large_sample', 'integer_like', 'mixed_variance', 'three_columns'
]


class TestCbookViolinMinMaxInvariantSuiteQA:
    @pytest.mark.parametrize("data_type", TEST_DATA_TYPES)
    def test_cbook_violin_min_max_invariant_suite_case(self, data_type):
        data = make_test_data(data_type)
        result = violin_stats(data, simple_method, points=100)
        
        # Verify we got results
        assert len(result) == len(data)
        
        # Verify each result has required keys and min <= max
        for stats, x in zip(result, data):
            assert 'min' in stats
            assert 'max' in stats
            assert stats['min'] <= stats['max']
