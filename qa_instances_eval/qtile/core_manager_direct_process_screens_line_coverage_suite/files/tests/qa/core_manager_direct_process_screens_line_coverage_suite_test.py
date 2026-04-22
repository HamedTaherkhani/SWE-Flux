from __future__ import annotations

import pytest

from libqtile.core import manager as manager_mod
from libqtile.core.manager import Qtile


class DummyInfo:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class DummyGap:
    pass


class DummyBar:
    finalize_total = 0

    def __init__(self, window=True):
        self.window = window

    def finalize(self):
        DummyBar.finalize_total += 1


class DummyScreen:
    def __init__(self, x=0, y=0, width=0, height=0, *, group=None, has_group=True, gaps=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.gaps = list(gaps or [])
        self.configure_calls = []
        if has_group:
            self.group = group

    def _configure(self, qtile, index, x, y, width, height, group, reconfigure_gaps=False):
        self.configure_calls.append(
            {
                "index": index,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "group": group,
                "reconfigure_gaps": reconfigure_gaps,
            }
        )
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.group = group


class DummyCore:
    def __init__(self, infos):
        self._infos = [DummyInfo(*i) for i in infos]

    def get_screen_info(self):
        return list(self._infos)


class DummyConfig:
    def __init__(self, screens=None, fake_screens=None):
        self.screens = list(screens or [])
        if fake_screens is not None:
            self.fake_screens = list(fake_screens)


class DummyQtileProcessScreensProbe:
    _process_screens = Qtile._process_screens

    def __init__(self, config, core, old_screens, available_groups, has_current_screen):
        self.config = config
        self.core = core
        self.screens = list(old_screens)
        self._available_groups = dict(available_groups)
        self.available_calls = []
        self.autogen_groups = []

        if has_current_screen and self.screens:
            self.current_screen = self.screens[0]

    def get_available_group(self, screen_idx):
        self.available_calls.append(screen_idx)
        return self._available_groups.get(screen_idx)

    def add_autogen_group(self, screen_idx):
        group = f"autogen-{screen_idx}-{len(self.autogen_groups)}"
        self.autogen_groups.append(group)
        return group


def dedup_core_infos(info_tuples):
    xywh = {}
    for x, y, w, h in info_tuples:
        cur_w, cur_h = xywh.get((x, y), (0, 0))
        xywh[(x, y)] = (max(cur_w, w), max(cur_h, h))
    return [(x, y, w, h) for (x, y), (w, h) in xywh.items()]


CASES = [
    {
        "name": "core_basic",
        "use_fake": False,
        "reloading": False,
        "has_current": True,
        "infos": [(0, 0, 800, 600)],
        "config_count": 1,
        "old_group_count": 1,
        "available": {},
        "missing_group_indices": set(),
        "shift_first_config": False,
        "include_stale": False,
    },
    {
        "name": "core_no_current_screen",
        "use_fake": False,
        "reloading": False,
        "has_current": False,
        "infos": [(0, 0, 1280, 720)],
        "config_count": 1,
        "old_group_count": 1,
        "available": {},
        "missing_group_indices": set(),
        "shift_first_config": False,
        "include_stale": False,
    },
    {
        "name": "core_reloading_sets_current",
        "use_fake": False,
        "reloading": True,
        "has_current": True,
        "infos": [(0, 0, 1280, 720), (1280, 0, 1280, 720)],
        "config_count": 2,
        "old_group_count": 2,
        "available": {},
        "missing_group_indices": set(),
        "shift_first_config": False,
        "include_stale": False,
    },
    {
        "name": "core_available_group_branch",
        "use_fake": False,
        "reloading": False,
        "has_current": False,
        "infos": [(0, 0, 1920, 1080), (1920, 0, 1920, 1080)],
        "config_count": 2,
        "old_group_count": 0,
        "available": {0: "avail-0", 1: "avail-1"},
        "missing_group_indices": set(),
        "shift_first_config": False,
        "include_stale": False,
    },
    {
        "name": "core_screen_constructor_branch",
        "use_fake": False,
        "reloading": False,
        "has_current": True,
        "infos": [(0, 0, 1200, 800), (1200, 0, 1200, 800)],
        "config_count": 1,
        "old_group_count": 1,
        "available": {1: "avail-1"},
        "missing_group_indices": set(),
        "shift_first_config": False,
        "include_stale": False,
    },
    {
        "name": "core_missing_group_attribute",
        "use_fake": False,
        "reloading": False,
        "has_current": True,
        "infos": [(0, 0, 900, 700), (900, 0, 900, 700)],
        "config_count": 2,
        "old_group_count": 2,
        "available": {},
        "missing_group_indices": {1},
        "shift_first_config": False,
        "include_stale": False,
    },
    {
        "name": "core_geometry_change_reconfigure",
        "use_fake": False,
        "reloading": False,
        "has_current": True,
        "infos": [(0, 0, 1000, 800)],
        "config_count": 1,
        "old_group_count": 1,
        "available": {},
        "missing_group_indices": set(),
        "shift_first_config": True,
        "include_stale": False,
    },
    {
        "name": "core_new_screen_reconfigure",
        "use_fake": False,
        "reloading": False,
        "has_current": True,
        "infos": [(0, 0, 1280, 720), (1280, 0, 1280, 720), (2560, 0, 1280, 720)],
        "config_count": 3,
        "old_group_count": 1,
        "available": {1: "avail-1", 2: "avail-2"},
        "missing_group_indices": set(),
        "shift_first_config": False,
        "include_stale": False,
    },
    {
        "name": "core_finalize_stale_bars",
        "use_fake": False,
        "reloading": False,
        "has_current": True,
        "infos": [(0, 0, 1600, 900)],
        "config_count": 1,
        "old_group_count": 1,
        "available": {},
        "missing_group_indices": set(),
        "shift_first_config": False,
        "include_stale": True,
    },
    {
        "name": "core_duplicate_position_aliasing",
        "use_fake": False,
        "reloading": False,
        "has_current": True,
        "infos": [(0, 0, 640, 480), (0, 0, 800, 600), (900, 0, 700, 500)],
        "config_count": 2,
        "old_group_count": 1,
        "available": {1: "avail-1"},
        "missing_group_indices": set(),
        "shift_first_config": False,
        "include_stale": False,
    },
]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
class TestCoreManagerDirectProcessScreensLineCoverageSuiteQA:
    def test_core_manager_direct_process_screens_line_coverage_suite_case(self, case, monkeypatch):
        original_screen = manager_mod.Screen
        original_bar = manager_mod.bar.Bar
        manager_mod.Screen = DummyScreen
        manager_mod.bar.Bar = DummyBar

        DummyBar.finalize_total = 0

        try:
            old_screens = []
            for idx in range(case["old_group_count"]):
                old_screens.append(
                    DummyScreen(
                        x=idx * 20,
                        y=0,
                        width=640,
                        height=480,
                        group=f"old-group-{idx}",
                        has_group=True,
                        gaps=[],
                    )
                )

            if case["include_stale"]:
                old_screens.append(
                    DummyScreen(
                        x=999,
                        y=999,
                        width=300,
                        height=200,
                        group="stale-group",
                        has_group=True,
                        gaps=[DummyBar(window=True), DummyBar(window=False), DummyGap()],
                    )
                )

            if case["use_fake"]:
                fake_screens = []
                for idx, (x, y, w, h) in enumerate(case["infos"]):
                    fake_screens.append(
                        DummyScreen(
                            x=x,
                            y=y,
                            width=w,
                            height=h,
                            group=f"cfg-fake-{idx}",
                            has_group=(idx not in case["missing_group_indices"]),
                            gaps=[],
                        )
                    )
                config = DummyConfig(screens=[], fake_screens=fake_screens)
                expected_count = len(fake_screens)
            else:
                dedup_infos = dedup_core_infos(case["infos"])
                expected_count = len(dedup_infos)
                config_screens = []
                for idx in range(case["config_count"]):
                    x, y, w, h = dedup_infos[idx]
                    if idx == 0 and case["shift_first_config"]:
                        x += 25
                    config_screens.append(
                        DummyScreen(
                            x=x,
                            y=y,
                            width=w,
                            height=h,
                            group=f"cfg-group-{idx}",
                            has_group=(idx not in case["missing_group_indices"]),
                            gaps=[],
                        )
                    )
                config = DummyConfig(screens=config_screens)

            probe = DummyQtileProcessScreensProbe(
                config=config,
                core=DummyCore(case["infos"]),
                old_screens=old_screens,
                available_groups=case["available"],
                has_current_screen=case["has_current"],
            )

            probe._process_screens(reloading=case["reloading"])

            assert len(probe.screens) == expected_count
            assert all(len(scr.configure_calls) == 1 for scr in probe.screens)

            if (not case["has_current"]) or case["reloading"]:
                assert probe.current_screen is probe.screens[0]

            if case["include_stale"]:
                assert DummyBar.finalize_total >= 1

            if case["name"] == "core_available_group_branch":
                assert probe.available_calls == [0, 1]

            if case["name"] == "core_duplicate_position_aliasing":
                assert len(probe.screens) == 2

        finally:
            manager_mod.Screen = original_screen
            manager_mod.bar.Bar = original_bar
