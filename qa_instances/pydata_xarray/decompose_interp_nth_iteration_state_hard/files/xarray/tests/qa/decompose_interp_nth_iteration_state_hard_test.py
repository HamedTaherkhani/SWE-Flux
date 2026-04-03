from __future__ import annotations

import numpy as np
import xarray as xr

from xarray.core.missing import decompose_interp


class TestDecomposeInterpNthIterationStateHardQA:
    def test_decompose_interp_nth_iteration_state_hard_case(self) -> None:
        indexes_coords = {
            "x": (
                np.array([0.0, 1.0], dtype=np.float64),
                xr.DataArray(np.zeros((2,), dtype=np.float64), dims=("lat",)),
            ),
            "y": (
                np.array([0.0, 1.0, 2.0], dtype=np.float64),
                xr.DataArray(np.zeros((3, 2), dtype=np.float64), dims=("time", "lat")),
            ),
            "z": (
                np.array([0.0, 1.0], dtype=np.float64),
                xr.DataArray(np.zeros((2,), dtype=np.float64), dims=("depth",)),
            ),
            "w": (
                np.array([0.0, 1.0], dtype=np.float64),
                xr.DataArray(np.zeros((2, 1), dtype=np.float64), dims=("depth", "member")),
            ),
            "v": (
                np.array([0.0, 1.0, 2.0], dtype=np.float64),
                xr.DataArray(np.zeros((3,), dtype=np.float64), dims=("member",)),
            ),
        }

        parts = list(decompose_interp(indexes_coords))

        assert isinstance(parts, list)
        assert len(parts) >= 2
        assert all(isinstance(p, dict) for p in parts)
