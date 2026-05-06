from __future__ import annotations

from reflex.style import convert_dict_to_style_and_format_emotion


class TestStyleEmotionFormatExecutionPathLinesQA:
    def test_style_emotion_format_execution_path_lines_case(self):
        raw_style = {
            "margin_x": "12px",
            "_hover": {
                "color": "tomato",
                "padding_y": ["2px", "4px"],
            },
            "font_size": ["12px", "14px", "16px"],
            "--accent-color": "teal",
        }

        emotion_style = convert_dict_to_style_and_format_emotion(raw_style)

        assert str(emotion_style["marginInlineStart"]) == '"12px"'
        assert str(emotion_style["marginInlineEnd"]) == '"12px"'
        assert str(emotion_style["&:hover"]["color"]) == '"tomato"'
        assert (
            str(
                emotion_style["&:hover"]["@media screen and (min-width: 30em)"][
                    "paddingTop"
                ]
            )
            == '"4px"'
        )
        assert (
            str(emotion_style["@media screen and (min-width: 48em)"]["fontSize"])
            == '"16px"'
        )
        assert str(emotion_style["--accent-color"]) == '"teal"'
