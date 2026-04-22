from types import SimpleNamespace

from libqtile.core.manager import Qtile


class DummyGroup:
    def __init__(self, name: str, screen=None, screen_affinity=None):
        self.name = name
        self.screen = screen
        self.screen_affinity = screen_affinity

    def __repr__(self) -> str:
        return f"DummyGroup({self.name})"


class DummyScreenConfig:
    def __init__(self, name: str, x: int, y: int, width: int, height: int):
        self.name = name
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
    ) -> None:
        self.index = index
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.group = grp
        self.reconfigure_gaps = reconfigure_gaps


class DummyInfo:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class DummyCore:
    def get_screen_info(self):
        return [
            DummyInfo(0, 0, 1000, 600),
            DummyInfo(0, 0, 1200, 700),
            DummyInfo(1200, 0, 800, 700),
            DummyInfo(1200, 0, 900, 650),
            DummyInfo(0, 700, 1000, 500),
            DummyInfo(1000, 700, 700, 500),
            DummyInfo(1000, 700, 650, 550),
        ]


class DummyQtileCoreProbe:
    _process_screens = Qtile._process_screens
    get_available_group = Qtile.get_available_group

    def __init__(self):
        old0 = DummyScreenConfig("old0", 0, 0, 1000, 600)
        old1 = DummyScreenConfig("old1", 1200, 0, 800, 700)
        self.screens = [old0, old1]

        g1 = DummyGroup("g1", screen=old0)
        g2 = DummyGroup("g2", screen=old1)
        g3 = DummyGroup("g3", screen=None, screen_affinity=2)
        g4 = DummyGroup("g4", screen=None, screen_affinity=0)

        self.groups = [g1, g2, g3, g4]
        self.groups_map = {g.name: g for g in self.groups}

        old0.group = g1
        old1.group = g2

        self.config = SimpleNamespace(
            screens=[
                DummyScreenConfig("cfg0", 5, 5, 1100, 650),
                DummyScreenConfig("cfg1", 1200, 10, 900, 680),
                DummyScreenConfig("cfg2", 0, 700, 1000, 500),
                DummyScreenConfig("cfg3", 900, 700, 600, 500),
            ]
        )
        self.core = DummyCore()
        self.autogen = []

    def add_autogen_group(self, screen_idx: int):
        group = DummyGroup(f"autogen_{screen_idx + 1}")
        self.groups.append(group)
        self.groups_map[group.name] = group
        self.autogen.append(group)
        return group


class TestCoreManagerProcessScreensConditionalVarStateQA:
    def test_core_manager_process_screens_conditional_var_state_case(self):
        probe = DummyQtileCoreProbe()

        # Directly call core function under test.
        probe._process_screens()

        assert [s.group.name for s in probe.screens] == ["g1", "g2", "g3", "autogen_4"]
        assert probe.screens[-1].width == 700
        assert probe.screens[-1].height == 550
