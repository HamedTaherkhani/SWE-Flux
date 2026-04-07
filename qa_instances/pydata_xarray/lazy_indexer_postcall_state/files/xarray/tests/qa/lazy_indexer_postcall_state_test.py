from __future__ import annotations

import numpy as np

from xarray.core.indexing import BasicIndexer, LazilyIndexedArray


class TestLazyIndexerPostcallStateHardQA:
    def test_lazy_indexer_postcall_state_case(self) -> None:
        base = np.arange(24, dtype=np.int64).reshape(4, 6)
        lazy = LazilyIndexedArray(
            base,
            BasicIndexer((slice(1, None, 2), slice(None, None, -1))),
        )

        refined = lazy[BasicIndexer((slice(1, 3), slice(2, 5, 2)))]

        assert isinstance(refined, LazilyIndexedArray)
        assert refined.shape == (1, 2)
        materialized = refined.get_duck_array()
        assert materialized.shape == (1, 2)
