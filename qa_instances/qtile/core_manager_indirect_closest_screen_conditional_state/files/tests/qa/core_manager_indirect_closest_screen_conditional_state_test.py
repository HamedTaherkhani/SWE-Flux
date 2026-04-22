from libqtile.core.manager import Qtile


class DummyScreen:
    def __init__(self, name: str, x: int, y: int, width: int, height: int):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __repr__(self) -> str:
        return f"DummyScreen({self.name})"


class DummyQtileCoreProbe:
    find_screen = Qtile.find_screen
    find_closest_screen = Qtile.find_closest_screen
    _find_closest_closest = Qtile._find_closest_closest

    def __init__(self, screens):
        self.screens = screens


class TestCoreManagerIndirectClosestScreenConditionalStateQA:
    def test_core_manager_indirect_closest_screen_conditional_state_case(self):
        screens = [
            DummyScreen("A", 1170, 33, 739, 497),
            DummyScreen("B", 1183, 15, 511, 486),
            DummyScreen("C", 1006, 843, 584, 584),
            DummyScreen("D", 328, 35, 833, 500),
            DummyScreen("E", 671, 77, 555, 631),
        ]

        qtile_probe = DummyQtileCoreProbe(screens)

        # Indirect chain: find_closest_screen -> _find_closest_closest.
        result = qtile_probe.find_closest_screen(1479, 91)

        assert result.name == "B"
