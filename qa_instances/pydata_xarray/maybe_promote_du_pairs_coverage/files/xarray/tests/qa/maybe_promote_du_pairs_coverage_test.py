import numpy as np

from xarray.core.dtypes import maybe_promote


class TestMaybePromoteDUPairsCoverageHardQA:
    def test_maybe_promote_du_pairs_coverage_case(self) -> None:
        out_float = maybe_promote(np.dtype("float64"))
        out_int = maybe_promote(np.dtype("int64"))
        out_complex = maybe_promote(np.dtype("complex128"))
        out_datetime = maybe_promote(np.dtype("datetime64[ns]"))
        out_object = maybe_promote(np.dtype("O"))

        assert str(out_float[0]) == "float64"
        assert str(out_int[0]) == "float64"
        assert str(out_complex[0]) == "complex128"
        assert str(out_datetime[0]).startswith("datetime64")
        assert str(out_object[0]) == "object"
