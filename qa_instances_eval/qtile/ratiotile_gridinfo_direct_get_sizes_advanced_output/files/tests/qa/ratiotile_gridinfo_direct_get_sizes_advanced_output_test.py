from libqtile.layout.ratiotile import GridInfo


class TestRatioTileGridInfoDirectGetSizesAdvancedOutputQA:
    def test_ratiotile_gridinfo_direct_get_sizes_advanced_output_case(self):
        grid = GridInfo(ratio=0.63, num_windows=13, width=711, height=1009)

        output_rectangles = grid.get_sizes_advanced(711, 1009, 17, 29)

        assert isinstance(output_rectangles, list)
        assert len(output_rectangles) == 13
        assert all(isinstance(rect, tuple) and len(rect) == 4 for rect in output_rectangles)
        assert output_rectangles[0] != output_rectangles[-1]
