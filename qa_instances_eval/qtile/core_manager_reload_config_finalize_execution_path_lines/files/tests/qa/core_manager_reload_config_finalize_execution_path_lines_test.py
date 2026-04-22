from types import SimpleNamespace

import libqtile.core.manager as manager_mod
from libqtile.core.manager import Qtile
from libqtile.core.state import QtileState


class DummyLayoutClone:
    def __init__(self, name: str):
        self.name = name
        self.finalize_calls = 0

    def finalize(self):
        self.finalize_calls += 1


class DummyGroup:
    def __init__(self, name: str, layout_name: str, label: str):
        self.name = name
        self.layout = SimpleNamespace(name=layout_name)
        self.label = label
        self.layouts = [
            DummyLayoutClone(f"{layout_name}_primary"),
            DummyLayoutClone(f"{layout_name}_secondary"),
        ]


class DummyScreen:
    def __init__(self, group: DummyGroup):
        self.group = group
        self.finalize_gaps_calls = 0

    def finalize_gaps(self):
        self.finalize_gaps_calls += 1


class DummyWidget:
    def __init__(self, name: str):
        self.name = name
        self.finalize_calls = 0

    def finalize(self):
        self.finalize_calls += 1


class DummyConfig:
    def __init__(self):
        self.load_calls = 0

    def load(self):
        self.load_calls += 1


class DummyCore:
    def __init__(self):
        self.ungrab_buttons_calls = 0

    def ungrab_buttons(self):
        self.ungrab_buttons_calls += 1


class DummyQtileReloadProbe:
    reload_config = Qtile.reload_config
    _finalize_configurables = Qtile._finalize_configurables

    def __init__(self):
        self.config = DummyConfig()
        self.core = DummyCore()

        g0 = DummyGroup("alpha", "max", "A")
        g1 = DummyGroup("beta", "columns", "B")
        g2 = DummyGroup("gamma", "stack", "C")

        self.groups = [g0, g1, g2]
        self.groups_map = {g.name: g for g in self.groups}

        s0 = DummyScreen(g0)
        s1 = DummyScreen(g1)
        self.screens = [s0, s1]
        self.current_screen = s0

        self.screen_refs = [s0, s1]
        self.layout_refs = []
        for group in self.groups:
            self.layout_refs.extend(group.layouts)

        self.widgets_map = {
            "clock": DummyWidget("clock"),
            "prompt": DummyWidget("prompt"),
            "memory": DummyWidget("memory"),
        }
        self.widget_refs = list(self.widgets_map.values())

        self.chord_stack = ["mod", "resize"]
        self._mouse_map = {1: "left", 3: "right"}

        self.ungrab_keys_calls = 0
        self.load_config_calls = 0

    def ungrab_keys(self):
        self.ungrab_keys_calls += 1

    def load_config(self):
        # Ensure cleanup path executes before reloading config.
        assert self.groups == []
        assert self.screens == []
        assert self.groups_map == {}
        assert self._mouse_map == {}
        assert self.chord_stack == []
        self.load_config_calls += 1


class TestCoreManagerReloadConfigFinalizeExecutionPathLinesQA:
    def test_core_manager_reload_config_finalize_execution_path_lines_case(self):
        probe = DummyQtileReloadProbe()

        remove_dbus_calls = []
        original_remove_dbus_rules = manager_mod.remove_dbus_rules
        manager_mod.remove_dbus_rules = lambda: remove_dbus_calls.append("called")

        try:
            probe.reload_config()
        finally:
            manager_mod.remove_dbus_rules = original_remove_dbus_rules

        assert probe.config.load_calls == 1
        assert isinstance(probe._state, QtileState)
        assert probe._state.restart is False
        assert probe._state.screens == {0: "alpha", 1: "beta"}
        assert probe._state.current_screen == 0

        assert all(widget.finalize_calls == 1 for widget in probe.widget_refs)
        assert all(layout.finalize_calls == 1 for layout in probe.layout_refs)
        assert all(screen.finalize_gaps_calls == 1 for screen in probe.screen_refs)

        assert probe.ungrab_keys_calls == 1
        assert probe.core.ungrab_buttons_calls == 1
        assert probe.load_config_calls == 1
        assert len(remove_dbus_calls) == 1

        assert probe.widgets_map == {}
        assert probe.groups == []
        assert probe.groups_map == {}
        assert probe.screens == []
        assert probe.chord_stack == []
        assert probe._mouse_map == {}
