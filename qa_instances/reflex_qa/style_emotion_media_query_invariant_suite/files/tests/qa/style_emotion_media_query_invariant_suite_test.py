from __future__ import annotations

from reflex.style import format_as_emotion


class TestStyleEmotionMediaQueryInvariantOneQA:
    def test_two_responsive_keys(self):
        result = format_as_emotion({"color": ["red", "blue"], "padding_x": ["1px", "2px"]})
        assert "@media screen and (min-width: 30em)" in result


class TestStyleEmotionMediaQueryInvariantTwoQA:
    def test_three_responsive_keys(self):
        result = format_as_emotion({"margin_y": ["1px", "2px"], "font_size": ["12px", "14px"]})
        assert "@media screen and (min-width: 30em)" in result


class TestStyleEmotionMediaQueryInvariantThreeQA:
    def test_nested_and_responsive(self):
        result = format_as_emotion({"border_color": ["red", "blue"], "_hover": {"color": "tomato"}})
        assert "&:hover" in result


class TestStyleEmotionMediaQueryInvariantFourQA:
    def test_three_breakpoints(self):
        result = format_as_emotion({"width": ["10px", "20px", "30px"], "height": ["1rem", "2rem"]})
        assert "@media screen and (min-width: 48em)" in result


class TestStyleEmotionMediaQueryInvariantFiveQA:
    def test_repeated_media_updates(self):
        result = format_as_emotion({"left": ["0", "1"], "right": ["2", "3"], "top": ["4", "5"]})
        assert "@media screen and (min-width: 30em)" in result


class TestStyleEmotionMediaQueryInvariantSixQA:
    def test_dict_inside_responsive_list(self):
        result = format_as_emotion({"_active": [{"color": "red"}, {"color": "blue"}], "gap": ["1", "2"]})
        assert "&:active" in result


class TestStyleEmotionMediaQueryInvariantSevenQA:
    def test_mixed_scalar_responsive(self):
        result = format_as_emotion({"display": "flex", "opacity": ["0", "1"], "z_index": ["1", "2"]})
        assert result["display"] == "flex"


class TestStyleEmotionMediaQueryInvariantEightQA:
    def test_four_key_merge(self):
        result = format_as_emotion({"a": ["1", "2"], "b": ["3", "4"], "c": ["5", "6"], "d": "7"})
        assert result["d"] == "7"


class TestStyleEmotionMediaQueryInvariantNineQA:
    def test_padding_and_margin(self):
        result = format_as_emotion({"padding": ["1px", "2px"], "margin": ["3px", "4px"]})
        assert "@media screen and (min-width: 30em)" in result


class TestStyleEmotionMediaQueryInvariantTenQA:
    def test_responsive_with_nested_selector(self):
        result = format_as_emotion({"color": ["red", "green"], ":focus": {"outline": "none"}})
        assert "&:focus" in result
