from types import SimpleNamespace

import libqtile.core.manager as manager_mod
from libqtile.core.manager import Qtile


class DummyGroup:
    def __init__(self, name: str, screen=None, screen_affinity=None):
        self.name = name
        self.screen = screen
        self.screen_affinity = screen_affinity

    def __repr__(self) -> str:
        return f"DummyGroup({self.name})"


class DummyInfo:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class DummyCore:
    def get_screen_info(self):
        # Repeated x/y entries force the xywh alias-merge path.
        return [
            DummyInfo(0, 0, 1200, 700),
            DummyInfo(0, 0, 1400, 840),
            DummyInfo(1400, 0, 900, 700),
            DummyInfo(1400, 0, 960, 730),
            DummyInfo(0, 900, 1100, 620),
            DummyInfo(1000, 900, 800, 640),
        ]


class DummyBarGap:
    def __init__(self, name: str, window):
        self.name = name
        self.window = window
        self.finalize_calls = 0

    def finalize(self):
        self.finalize_calls += 1


class DummyScreenObj:
    def __init__(self, name: str = "auto", x: int = 0, y: int = 0, width: int = 0, height: int = 0):
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


class DummyQtileCoreProbe:
    _process_screens = Qtile._process_screens
    get_available_group = Qtile.get_available_group

    def __init__(self):
        old0 = DummyScreenObj("old0", 0, 0, 1200, 700)
        old1 = DummyScreenObj("old1", 1300, 0, 700, 650)

        self.old0_gap = DummyBarGap("old0gap", object())
        self.old1_gap_skip = DummyBarGap("old1skip", None)
        self.old1_gap_finalize = DummyBarGap("old1final", object())

        old0.gaps = [self.old0_gap]
        old1.gaps = [self.old1_gap_skip, self.old1_gap_finalize]

        self.screens = [old0, old1]

        g1 = DummyGroup("g1", screen=old0)
        g2 = DummyGroup("g2", screen=old1)
        g3 = DummyGroup("g3", screen=None, screen_affinity=2)
        g4 = DummyGroup("g4", screen=None, screen_affinity=99)

        old0.group = g1
        old1.group = g2

        self.groups = [g1, g2, g3, g4]
        self.groups_map = {g.name: g for g in self.groups}

        # cfg1 has a pre-existing group attr so `if not hasattr(scr, "group")` differs per iteration.
        cfg0 = DummyScreenObj("cfg0", 5, 5, 1000, 600)
        cfg1 = DummyScreenObj("cfg1", 1400, 0, 960, 730)
        cfg1.group = g2
        cfg2 = DummyScreenObj("cfg2", 0, 900, 1080, 600)

        self.config = SimpleNamespace(screens=[cfg0, cfg1, cfg2])
        self.core = DummyCore()

        self.current_screen = old1
        self.autogen_groups = []

    def add_autogen_group(self, screen_idx: int):
        group = DummyGroup(f"autogen_{screen_idx + 1}")
        self.groups.append(group)
        self.groups_map[group.name] = group
        self.autogen_groups.append(group.name)
        return group


class TestCoreManagerDirectProcessScreensExecutionPathLinesQA:
    def test_core_manager_direct_process_screens_execution_path_lines_case(self):
        probe = DummyQtileCoreProbe()

        original_screen_cls = manager_mod.Screen
        original_bar_cls = manager_mod.bar.Bar

        # Make _process_screens deterministic and runnable with lightweight stubs.
        manager_mod.Screen = DummyScreenObj
        manager_mod.bar.Bar = DummyBarGap
        try:
            probe._process_screens(reloading=True)
        finally:
            manager_mod.Screen = original_screen_cls
            manager_mod.bar.Bar = original_bar_cls

        assert len(probe.screens) == 4
        assert [screen.group.name for screen in probe.screens] == ["g1", "g2", "g3", "autogen_4"]
        assert probe.autogen_groups == ["autogen_4"]

        # Removed old screens trigger finalize path for bar gaps with a window.
        assert probe.old0_gap.finalize_calls == 1
        assert probe.old1_gap_skip.finalize_calls == 0
        assert probe.old1_gap_finalize.finalize_calls == 1
