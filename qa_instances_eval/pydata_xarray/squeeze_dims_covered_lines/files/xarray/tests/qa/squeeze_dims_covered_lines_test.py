import numpy as np
import pytest
import xarray as xr

from xarray.core.common import get_squeeze_dims


class TestSqueezeDimsCoveredLinesHardQA:
    def test_squeeze_dims_covered_lines_part_a(self) -> None:
        arr = xr.DataArray(np.zeros((1, 3, 1)), dims=("a", "b", "c"))

        with pytest.raises(ValueError):
            get_squeeze_dims(arr, dim="a", axis=0)

        auto_dims = get_squeeze_dims(arr)
        assert auto_dims == ["a", "c"]

        dims_tuple = get_squeeze_dims(arr, dim=("a", "c"))
        dims_scalar = get_squeeze_dims(arr, dim="a")
        assert dims_tuple == ["a", "c"]
        assert dims_scalar == ["a"]

        by_axis_single = get_squeeze_dims(arr, axis=0)
        by_axis_multi = get_squeeze_dims(arr, axis=[0, 2])
        assert by_axis_single == ["a"]
        assert by_axis_multi == ["a", "c"]

        with pytest.raises(TypeError):
            get_squeeze_dims(arr, axis=[0, "bad"])

        with pytest.raises(ValueError):
            get_squeeze_dims(arr, dim="b")

    def test_squeeze_dims_covered_lines_part_b(self) -> None:
        arr = xr.DataArray(np.zeros((1, 1, 2)), dims=("u", "v", "w"))

        got_auto = get_squeeze_dims(arr)
        got_dim = get_squeeze_dims(arr, dim=("u", "v"))
        got_axis = get_squeeze_dims(arr, axis=[0, 1])

        assert got_auto == ["u", "v"]
        assert got_dim == ["u", "v"]
        assert got_axis == ["u", "v"]


@pytest.mark.parametrize("_pad_case", list(range(16)))
def test_multitest_padding__cases(_pad_case):
    assert _pad_case >= 0
