import sys
from pathlib import Path
import pytest

# CRITICAL: Force local matplotlib import
testbed_path = Path("/testbed")
lib_path = testbed_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Now import from local source
from matplotlib.category import UnitData


# Generate diverse test data to exercise the update method
TEST_DATA = [
    ['a', 'b', 'c'],
    ['x', 'y', 'z', 'w'],
    ['1', '2', '3'],
    ['alpha', 'beta'],
    ['cat', 'dog', 'bird', 'fish', 'rabbit'],
    ['A', 'B'],
    ['foo', 'bar', 'baz'],
    [b'byte1', b'byte2'],
    ['single'],
    ['red', 'green', 'blue', 'yellow'],
    ['one', 'two', 'three', 'four', 'five'],
    ['first', 'second'],
    ['north', 'south', 'east', 'west'],
    ['jan', 'feb', 'mar'],
    ['alice', 'bob', 'charlie', 'david'],
    ['10', '20', '30'],
    ['p', 'q', 'r', 's'],
    ['test1', 'test2', 'test3'],
    ['val1', 'val2'],
    ['item', 'thing', 'object'],
    ['a1', 'a2', 'a3', 'a4'],
    ['left', 'right', 'center'],
    ['up', 'down'],
    ['true', 'false'],
]


class TestCategoryUnitDataMappingInvariantSuiteQA:
    @pytest.mark.parametrize("data", TEST_DATA)
    def test_category_unit_data_mapping_invariant_suite_case(self, data):
        unit_data = UnitData()
        unit_data.update(data)
        assert len(unit_data._mapping) == len(data)
        # Verify all data items are in mapping
        for item in data:
            assert item in unit_data._mapping
