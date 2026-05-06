from __future__ import annotations

from reflex.components.core.breakpoints import Breakpoints
from reflex.style import convert


class TestStyleConvertDefUsePairsQA:
    def test_style_convert_def_use_pairs_case(self):
        raw_style = Breakpoints.create(
            initial={
                "margin_x": "1rem",
                "_hover": {"color": "tomato", "padding_y": ["2px", "4px"]},
            },
            xs={
                "border_color": "plum",
                "padding_x": ["3px", "5px", "7px"],
            },
            md={
                "font_size": ["12px", "14px"],
                "--accent-color": "teal",
            },
        )

        converted, var_data = convert(raw_style)

        assert list(converted.keys()) == ["0px", "30em", "62em"]
        assert str(converted["0px"]["marginInlineStart"]) == '"1rem"'
        assert str(converted["0px"]["marginInlineEnd"]) == '"1rem"'
        assert str(converted["0px"]["_hover"]["color"]) == '"tomato"'
        assert str(converted["0px"]["_hover"]["paddingTop"][1]) == '"4px"'
        assert str(converted["30em"]["borderColor"]) == '"plum"'
        assert str(converted["30em"]["paddingInlineStart"][2]) == '"7px"'
        assert str(converted["62em"]["fontSize"][0]) == '"12px"'
        assert str(converted["62em"]["--accent-color"]) == '"teal"'
        assert var_data is None
