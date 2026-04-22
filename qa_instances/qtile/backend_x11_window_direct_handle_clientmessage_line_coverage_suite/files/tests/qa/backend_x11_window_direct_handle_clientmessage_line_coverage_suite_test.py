from __future__ import annotations

from types import SimpleNamespace

import pytest

from libqtile.backend.x11 import window as window_mod
from libqtile.backend.x11.window import (
    IconicState,
    NormalState,
    Window,
    _NET_WM_STATE_ADD,
    _NET_WM_STATE_REMOVE,
    _NET_WM_STATE_TOGGLE,
)


class FakeAtoms(dict):
    def get_name(self, opcode):
        for name, value in self.items():
            if value == opcode:
                return name
        return f"UNKNOWN_{opcode}"


class FakeX11Window:
    def __init__(self, state_atoms=None):
        self.state_atoms = list(state_atoms or [])
        self.set_property_calls = []

    def get_property(self, name, _prop_type=None, unpack=None):
        if name == "_NET_WM_STATE":
            return list(self.state_atoms)
        return []

    def set_property(self, name, value):
        data = list(value)
        self.set_property_calls.append((name, data))
        if name == "_NET_WM_STATE":
            self.state_atoms = data


class FakeScreen:
    def __init__(self, name):
        self.name = name
        self.set_group_calls = []

    def set_group(self, group):
        self.set_group_calls.append(group.name)


class FakeGroup:
    def __init__(self, name, screen=None):
        self.name = name
        self.screen = screen
        self.focus_calls = []

    def focus(self, win):
        self.focus_calls.append(win)


class FakeDropdown:
    def __init__(self, window=None):
        self.window = window
        self.show_calls = 0

    def show(self):
        self.show_calls += 1


class FakeScratchPadGroup:
    def __init__(self, name, screen=None, dropdowns=None):
        self.name = name
        self.screen = screen
        self.dropdowns = dict(dropdowns or {})
        self.focus_calls = []

    def focus(self, win):
        self.focus_calls.append(win)


class DummyQtile:
    def __init__(self, atoms, focus_behavior, auto_minimize, current_screen):
        self.core = SimpleNamespace(conn=SimpleNamespace(atoms=atoms))
        self.config = SimpleNamespace(
            focus_on_window_activation=focus_behavior,
            auto_minimize=auto_minimize,
        )
        self.current_screen = current_screen
        self.groups = [FakeGroup("g0"), FakeGroup("g1"), FakeGroup("g2")]


class DummyHandleClientMessageProbe:
    handle_ClientMessage = Window.handle_ClientMessage

    def __init__(self, qtile, group, x11_window, minimized=False):
        self.qtile = qtile
        self.group = group
        self.window = x11_window
        self.minimized = minimized
        self.urgent = False

        self.bring_to_front_calls = 0
        self.kill_calls = 0
        self.togroup_calls = []

    def bring_to_front(self):
        self.bring_to_front_calls += 1

    def kill(self):
        self.kill_calls += 1

    def togroup(self, group_name):
        self.togroup_calls.append(group_name)


def make_event(opcode, data32):
    padded = list(data32) + [0] * max(0, 5 - len(data32))
    return SimpleNamespace(type=opcode, data=SimpleNamespace(data32=padded))


CASES = [
    {
        "name": "wm_state_add",
        "opcode_key": "_NET_WM_STATE",
        "data32": [_NET_WM_STATE_ADD, 3002, 0],
        "initial_state": [3001],
    },
    {
        "name": "wm_state_toggle",
        "opcode_key": "_NET_WM_STATE",
        "data32": [_NET_WM_STATE_TOGGLE, 3001, 3003],
        "initial_state": [3001],
    },
    {
        "name": "active_window_pager_source",
        "opcode_key": "_NET_ACTIVE_WINDOW",
        "data32": [2],
    },
    {
        "name": "active_focus_behavior_focus",
        "opcode_key": "_NET_ACTIVE_WINDOW",
        "data32": [1],
        "focus_behavior": "focus",
    },
    {
        "name": "active_focus_behavior_focus_scratchpad",
        "opcode_key": "_NET_ACTIVE_WINDOW",
        "data32": [1],
        "focus_behavior": "focus",
        "group_type": "scratchpad",
        "group_screen": "current",
        "dropdown_has_self": True,
    },
    {
        "name": "active_focus_behavior_smart_offscreen_sets_urgent",
        "opcode_key": "_NET_ACTIVE_WINDOW",
        "data32": [1],
        "focus_behavior": "smart",
        "group_screen": "other",
    },
    {
        "name": "active_focus_behavior_smart_onscreen_focuses",
        "opcode_key": "_NET_ACTIVE_WINDOW",
        "data32": [1],
        "focus_behavior": "smart",
        "group_screen": "current",
    },
    {
        "name": "active_focus_behavior_urgent",
        "opcode_key": "_NET_ACTIVE_WINDOW",
        "data32": [1],
        "focus_behavior": "urgent",
    },
    {
        "name": "active_focus_behavior_never",
        "opcode_key": "_NET_ACTIVE_WINDOW",
        "data32": [1],
        "focus_behavior": "never",
    },
    {
        "name": "active_focus_behavior_callable_true",
        "opcode_key": "_NET_ACTIVE_WINDOW",
        "data32": [1],
        "focus_behavior": "callable_true",
    },
    {
        "name": "active_focus_behavior_invalid_value",
        "opcode_key": "_NET_ACTIVE_WINDOW",
        "data32": [1],
        "focus_behavior": "mystery",
    },
    {
        "name": "close_window_branch",
        "opcode_key": "_NET_CLOSE_WINDOW",
        "data32": [0],
    },
    {
        "name": "wm_change_state_normal",
        "opcode_key": "WM_CHANGE_STATE",
        "data32": [NormalState],
        "initial_minimized": True,
    },
    {
        "name": "wm_change_state_iconic_auto_minimize",
        "opcode_key": "WM_CHANGE_STATE",
        "data32": [IconicState],
        "auto_minimize": True,
    },
    {
        "name": "wm_change_state_iconic_auto_minimize_false",
        "opcode_key": "WM_CHANGE_STATE",
        "data32": [IconicState],
        "auto_minimize": False,
        "initial_minimized": False,
    },
    {
        "name": "wm_desktop_valid_index",
        "opcode_key": "_NET_WM_DESKTOP",
        "data32": [1],
    },
    {
        "name": "wm_desktop_invalid_index",
        "opcode_key": "_NET_WM_DESKTOP",
        "data32": [99],
    },
    {
        "name": "unhandled_opcode",
        "opcode": 7777,
        "data32": [0],
    },
]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
class TestBackendX11WindowDirectHandleClientmessageLineCoverageSuiteQA:
    def test_backend_x11_window_direct_handle_clientmessage_line_coverage_suite_case(
        self, case, monkeypatch
    ):
        debug_calls = []
        warning_calls = []
        hook_fire_calls = []

        monkeypatch.setattr(window_mod, "ScratchPad", FakeScratchPadGroup)
        monkeypatch.setattr(window_mod.logger, "debug", lambda *a, **k: debug_calls.append((a, k)))
        monkeypatch.setattr(window_mod.logger, "warning", lambda *a, **k: warning_calls.append((a, k)))
        monkeypatch.setattr(window_mod.hook, "fire", lambda *a, **k: hook_fire_calls.append((a, k)))

        atoms = FakeAtoms(
            {
                "_NET_WM_STATE": 101,
                "_NET_ACTIVE_WINDOW": 102,
                "_NET_CLOSE_WINDOW": 103,
                "WM_CHANGE_STATE": 104,
                "_NET_WM_DESKTOP": 105,
            }
        )

        current_screen = FakeScreen("current")
        other_screen = FakeScreen("other")

        raw_focus_behavior = case.get("focus_behavior", "focus")
        if raw_focus_behavior == "callable_true":
            def focus_behavior(win):
                return win.group is not None
        else:
            focus_behavior = raw_focus_behavior

        qtile = DummyQtile(
            atoms=atoms,
            focus_behavior=focus_behavior,
            auto_minimize=case.get("auto_minimize", True),
            current_screen=current_screen,
        )

        group_screen_kind = case.get("group_screen", "current")
        if group_screen_kind == "current":
            group_screen = current_screen
        elif group_screen_kind == "other":
            group_screen = other_screen
        else:
            group_screen = None

        if case.get("group_type") == "scratchpad":
            dropdown = FakeDropdown(window=None)
            group = FakeScratchPadGroup("sp", screen=group_screen, dropdowns={"d1": dropdown})
        else:
            dropdown = None
            group = FakeGroup("g-target", screen=group_screen)

        x11_window = FakeX11Window(case.get("initial_state", []))
        probe = DummyHandleClientMessageProbe(
            qtile=qtile,
            group=group,
            x11_window=x11_window,
            minimized=case.get("initial_minimized", False),
        )

        if dropdown is not None and case.get("dropdown_has_self", False):
            dropdown.window = probe

        if "opcode" in case:
            opcode = case["opcode"]
        else:
            opcode = atoms[case["opcode_key"]]
        event = make_event(opcode, case.get("data32", [0]))

        probe.handle_ClientMessage(event)

        name = case["name"]

        if name == "wm_state_add":
            assert x11_window.set_property_calls
            assert set(x11_window.state_atoms) == {3001, 3002}

        elif name == "wm_state_toggle":
            assert x11_window.set_property_calls
            assert set(x11_window.state_atoms) == {3003}

        elif name == "active_window_pager_source":
            assert current_screen.set_group_calls == [group.name]
            assert group.focus_calls == [probe]
            assert probe.bring_to_front_calls == 1

        elif name == "active_focus_behavior_focus":
            assert current_screen.set_group_calls == [group.name]
            assert group.focus_calls == [probe]
            assert probe.urgent is False

        elif name == "active_focus_behavior_focus_scratchpad":
            assert dropdown is not None
            assert dropdown.show_calls == 1
            assert current_screen.set_group_calls == []
            assert group.focus_calls == []

        elif name == "active_focus_behavior_smart_offscreen_sets_urgent":
            assert probe.urgent is True
            assert any(args and args[0] == "client_urgent_hint_changed" for args, _ in hook_fire_calls)

        elif name == "active_focus_behavior_smart_onscreen_focuses":
            assert current_screen.set_group_calls == [group.name]
            assert group.focus_calls == [probe]

        elif name == "active_focus_behavior_urgent":
            assert probe.urgent is True
            assert any(args and args[0] == "client_urgent_hint_changed" for args, _ in hook_fire_calls)

        elif name == "active_focus_behavior_never":
            assert probe.urgent is False
            assert current_screen.set_group_calls == []
            assert group.focus_calls == []

        elif name == "active_focus_behavior_callable_true":
            assert current_screen.set_group_calls == [group.name]
            assert group.focus_calls == [probe]

        elif name == "active_focus_behavior_invalid_value":
            assert current_screen.set_group_calls == []
            assert group.focus_calls == []
            assert any(
                args and "Invalid value for focus_on_window_activation" in str(args[0])
                for args, _ in debug_calls
            )

        elif name == "close_window_branch":
            assert probe.kill_calls == 1

        elif name == "wm_change_state_normal":
            assert probe.minimized is False

        elif name == "wm_change_state_iconic_auto_minimize":
            assert probe.minimized is True

        elif name == "wm_change_state_iconic_auto_minimize_false":
            assert probe.minimized is False

        elif name == "wm_desktop_valid_index":
            assert probe.togroup_calls == ["g1"]

        elif name == "wm_desktop_invalid_index":
            assert len(warning_calls) >= 1

        elif name == "unhandled_opcode":
            assert any(args and "Unhandled client message" in str(args[0]) for args, _ in debug_calls)
