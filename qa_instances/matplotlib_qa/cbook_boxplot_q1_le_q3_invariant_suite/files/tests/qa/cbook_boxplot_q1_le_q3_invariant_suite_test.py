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
from matplotlib.cbook import boxplot_stats


# Generate diverse datasets for boxplot statistics
def make_test_data(data_type, size=100):
    """Create different distributions for testing."""
    np.random.seed(hash(data_type) % (2**32))  # Reproducible but varied
    
    if data_type == 'normal':
        return np.random.randn(size)
    elif data_type == 'uniform':
        return np.random.uniform(-10, 10, size)
    elif data_type == 'exponential':
        return np.random.exponential(2.0, size)
    elif data_type == 'bimodal':
        return np.concatenate([np.random.randn(size//2), np.random.randn(size//2) + 5])
    elif data_type == 'skewed_right':
        return np.random.gamma(2, 2, size)
    elif data_type == 'skewed_left':
        return -np.random.gamma(2, 2, size)
    elif data_type == 'heavy_tails':
        return np.random.standard_t(3, size)
    elif data_type == 'constant':
        return np.ones(size) * 5.0
    elif data_type == 'with_outliers':
        data = np.random.randn(size)
        data[::10] = np.random.uniform(-50, 50, size//10)
        return data
    elif data_type == 'small_iqr':
        return np.random.uniform(4.9, 5.1, size)
    elif data_type == 'large_range':
        return np.random.uniform(-1000, 1000, size)
    elif data_type == 'integer_like':
        return np.round(np.random.randn(size) * 10)
    elif data_type == 'positive_only':
        return np.abs(np.random.randn(size)) + 1
    elif data_type == 'negative_only':
        return -np.abs(np.random.randn(size)) - 1
    elif data_type == 'mixed_variance':
        part1 = np.random.randn(size//2) * 0.1
        part2 = np.random.randn(size//2) * 5.0
        return np.concatenate([part1, part2])
    elif data_type == 'triangular':
        return np.random.triangular(-5, 0, 5, size)
    elif data_type == 'beta':
        return np.random.beta(2, 5, size) * 10
    elif data_type == 'lognormal':
        return np.random.lognormal(0, 1, size)
    elif data_type == 'pareto':
        return np.random.pareto(3, size) + 1
    elif data_type == 'weibull':
        return np.random.weibull(1.5, size)
    elif data_type == 'chi_square':
        return np.random.chisquare(5, size)
    elif data_type == 'laplace':
        return np.random.laplace(0, 2, size)
    elif data_type == 'logistic':
        return np.random.logistic(0, 2, size)
    elif data_type == 'gumbel':
        return np.random.gumbel(0, 2, size)
    else:  # 'cauchy'
        return np.random.standard_cauchy(size)


TEST_DATA_TYPES = [
    'normal', 'uniform', 'exponential', 'bimodal', 'skewed_right', 'skewed_left',
    'heavy_tails', 'constant', 'with_outliers', 'small_iqr', 'large_range',
    'integer_like', 'positive_only', 'negative_only', 'mixed_variance',
    'triangular', 'beta', 'lognormal', 'pareto', 'weibull',
    'chi_square', 'laplace', 'logistic', 'gumbel', 'cauchy'
]


class TestCbookBoxplotQ1LeQ3InvariantSuiteQA:
    @pytest.mark.parametrize("data_type", TEST_DATA_TYPES)
    def test_cbook_boxplot_q1_le_q3_invariant_suite_case(self, data_type):
        data = make_test_data(data_type, size=100)
        result = boxplot_stats([data])
        
        # Verify we got a result
        assert len(result) == 1
        stats = result[0]
        
        # Verify q1 <= q3 (by definition of quartiles)
        assert stats['q1'] <= stats['q3']
        assert stats['iqr'] >= 0
