import pytest

from xarray.core.indexing import expanded_indexer


class TestExpandedIndexerLenRangeMultitestHardQA:
    def test_expanded_indexer_len_range_multitest_hard_part_a(self) -> None:
        out1 = expanded_indexer(2, ndim=1)
        out2 = expanded_indexer((0, 1), ndim=3)
        out3 = expanded_indexer((Ellipsis, 1), ndim=4)

        assert len(out1) == 1
        assert len(out2) == 3
        assert len(out3) == 4

    def test_expanded_indexer_len_range_multitest_hard_part_b(self) -> None:
        with pytest.raises(IndexError):
            expanded_indexer((0, 1, 2), ndim=2)

        with pytest.raises(IndexError):
            expanded_indexer((0, 1, 2, 3, 4), ndim=2)

        out4 = expanded_indexer((Ellipsis, Ellipsis, 0), ndim=2)
        assert len(out4) == 2
