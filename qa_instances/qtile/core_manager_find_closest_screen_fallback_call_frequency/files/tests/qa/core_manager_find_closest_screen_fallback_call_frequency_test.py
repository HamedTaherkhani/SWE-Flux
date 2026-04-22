from libqtile.core.manager import Qtile


class DummyScreen:
    def __init__(self, name: str, x: int, y: int, width: int, height: int):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class DummyQtileClosestScreenProbe:
    find_screen = Qtile.find_screen
    find_closest_screen = Qtile.find_closest_screen
    _find_closest_closest = Qtile._find_closest_closest

    def __init__(self):
        self.screens = [
            DummyScreen("A", 0, 0, 360, 300),
            DummyScreen("B", 220, 40, 420, 340),
            DummyScreen("C", 80, 240, 380, 360),
            DummyScreen("D", 460, 220, 420, 360),
            DummyScreen("E", 700, -60, 260, 260),
        ]


def build_queries() -> list[tuple[int, int]]:
    queries: list[tuple[int, int]] = []
    for gx in range(-180, 980, 140):
        for gy in range(-140, 920, 160):
            if ((gx // 140) - (gy // 160)) % 4 != 1:
                qx = gx + ((gy // 160) % 3) * 17 - 9
                qy = gy - ((gx // 140) % 2) * 23 + 11
                queries.append((qx, qy))
    return queries


class TestCoreManagerFindClosestScreenFallbackCallFrequencyQA:
    def test_core_manager_find_closest_screen_fallback_call_frequency_case(self):
        probe = DummyQtileClosestScreenProbe()

        queries = build_queries()
        chosen = []

        for idx, (x, y) in enumerate(queries):
            if idx % 6 == 2:
                x += 53
            if idx % 5 == 1:
                y -= 41
            screen = probe.find_closest_screen(x, y)
            chosen.append(screen.name)

        assert len(queries) == 47
        assert len(chosen) == 47
        assert len(set(chosen)) >= 4
        assert chosen[:6] == ["A", "E", "C", "C", "A", "A"]
