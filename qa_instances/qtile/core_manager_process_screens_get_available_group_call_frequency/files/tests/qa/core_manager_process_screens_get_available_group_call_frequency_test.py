from types import SimpleNamespace

from libqtile.core.manager import Qtile


class DummyGroup:
    def __init__(self, name: str, screen=None, screen_affinity=None):
        self.name = name
        self.screen = screen
        self.screen_affinity = screen_affinity


class DummyScreen:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.gaps = []

    def _configure(
        self,
        qtile,
        index: int,
        x: int,
        y: int,
        width: int,
        height: int,
        grp,
        reconfigure_gaps: bool = False,
    ):
        self.index = index
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.group = grp
        self.reconfigure_gaps = reconfigure_gaps
        if grp is not None:
            grp.screen = self


class DummyQtileProcessScreensProbe:
    _process_screens = Qtile._process_screens
    get_available_group = Qtile.get_available_group

    def __init__(self):
        g0 = DummyGroup("g0")
        g1 = DummyGroup("g1")

        old0 = DummyScreen(0, 0, 640, 480)
        old1 = DummyScreen(640, 0, 640, 480)
        old0.group = g0
        old1.group = g1
        g0.screen = old0
        g1.screen = old1

        self.screens = [old0, old1]
        self.current_screen = old0

        self.groups = [g0, g1]
        for idx in range(2, 40):
            affinity = None if idx % 5 else 99
            self.groups.append(DummyGroup(f"g{idx}", screen=None, screen_affinity=affinity))
        self.groups_map = {g.name: g for g in self.groups}

        self.autogen_calls = 0

        self.config = SimpleNamespace(fake_screens=[])

    def add_autogen_group(self, screen_idx: int):
        grp = DummyGroup(f"autogen_{screen_idx + 1}", screen=None, screen_affinity=screen_idx)
        self.groups.append(grp)
        self.groups_map[grp.name] = grp
        self.autogen_calls += 1
        return grp


def build_fake_screens(n: int, phase: int) -> list[DummyScreen]:
    screens = []
    for i in range(n):
        x = 15 + i * (97 + phase * 3)
        y = (i % 4) * 73 + phase * 11
        width = 540 + (i % 3) * 41
        height = 330 + (i % 5) * 29
        screens.append(DummyScreen(x, y, width, height))
    return screens


class TestCoreManagerProcessScreensGetAvailableGroupCallFrequencyQA:
    def test_core_manager_process_screens_get_available_group_call_frequency_case(self):
        probe = DummyQtileProcessScreensProbe()

        phase_sizes = [
            len([i for i in range(16) if i % 2 == 0]),
            len([i for i in range(20) if i % 3 != 1]),
            len([i for i in range(18) if i % 5 in (0, 2, 4)]),
        ]

        for phase_idx, size in enumerate(phase_sizes):
            probe.config.fake_screens = build_fake_screens(size, phase_idx)
            probe._process_screens(reloading=True)

        assert phase_sizes == [8, 13, 11]
        assert len(probe.screens) == 11
        assert probe.autogen_calls == 0
        assert probe.current_screen is probe.screens[0]
        assert all(screen.group is not None for screen in probe.screens)
