import xarray as xr


class TestConcatMissingVarIndexStateHardQA:
    def test_concat_missing_var_index_state_hard_case(self) -> None:
        ds1 = xr.Dataset(
            data_vars={
                "a": ("x", [1, 2]),
                "temp": ("x", [10, 20]),
            },
            coords={"x": [0, 1]},
        )
        ds2 = xr.Dataset(
            data_vars={
                "a": ("x", [3, 4]),
            },
            coords={"x": [0, 1]},
        )

        out = xr.concat([ds1, ds2], dim="sample", data_vars="all", coords="minimal")
        assert "temp" in out.data_vars
        assert out.sizes["sample"] == 2
