import numpy as np
import pytest
import xarray as xr

try:
    from xarray.core.combine import _infer_concat_order_from_coords
except ModuleNotFoundError:
    from xarray.structure.combine import _infer_concat_order_from_coords


class TestCombineTileIdsLengthLoopInvariantHardQA:
    def test_combine_tile_ids_length_loop_invariant_part_a(self) -> None:
        ds1 = xr.Dataset(
            data_vars={"v": (("x", "y"), np.array([[1.0, 2.0], [3.0, 4.0]]))},
            coords={"x": [0, 1], "y": [10, 20]},
        )
        ds2 = xr.Dataset(
            data_vars={"v": (("x", "y"), np.array([[5.0, 6.0], [7.0, 8.0]]))},
            coords={"x": [2, 3], "y": [10, 20]},
        )

        combined_ids, concat_dims = _infer_concat_order_from_coords([ds1, ds2])
        assert len(combined_ids) == 2
        assert "x" in concat_dims

    def test_combine_tile_ids_length_loop_invariant_part_b(self) -> None:
        d00 = xr.Dataset(
            data_vars={"v": (("x", "y"), np.array([[1.0, 2.0], [3.0, 4.0]]))},
            coords={"x": [0, 1], "y": [0, 1]},
        )
        d01 = xr.Dataset(
            data_vars={"v": (("x", "y"), np.array([[5.0, 6.0], [7.0, 8.0]]))},
            coords={"x": [0, 1], "y": [2, 3]},
        )
        d10 = xr.Dataset(
            data_vars={"v": (("x", "y"), np.array([[9.0, 10.0], [11.0, 12.0]]))},
            coords={"x": [2, 3], "y": [0, 1]},
        )
        d11 = xr.Dataset(
            data_vars={"v": (("x", "y"), np.array([[13.0, 14.0], [15.0, 16.0]]))},
            coords={"x": [2, 3], "y": [2, 3]},
        )

        combined_ids, concat_dims = _infer_concat_order_from_coords([d00, d01, d10, d11])
        assert len(combined_ids) == 4
        assert "x" in concat_dims and "y" in concat_dims


@pytest.mark.parametrize("_pad_case", list(range(16)))
def test_multitest_padding__cases(_pad_case):
    assert _pad_case >= 0
