from libqtile.layout.spiral import Spiral


class TestLayoutSpiralDirectGetSpiralOutputQA:
    def test_layout_spiral_direct_get_spiral_output_case(self):
        spiral = Spiral(
            main_pane="left",
            clockwise=True,
            ratio=0.71,
            main_pane_ratio=None,
            margin=[9, 14, 6, 12],
            border_width=4,
        )

        # Directly seed a non-trivial number of pseudo-clients.
        spiral.clients.clients = [object() for _ in range(15)]

        output_rectangles = spiral.get_spiral(23, 47, 1621, 941)

        assert isinstance(output_rectangles, list)
        assert output_rectangles
        assert all(isinstance(rect, tuple) and len(rect) == 4 for rect in output_rectangles)
        assert output_rectangles[0][2] > output_rectangles[-1][2]
