from libqtile.backend.x11 import window as x11_window_mod
from libqtile.backend.x11.window import Window


class _DummyData:
    def __init__(self, data32):
        self.data32 = data32


class _DummyEvent:
    def __init__(self, opcode, data32):
        self.type = opcode
        self.data = _DummyData(data32)


class _DummyAtoms(dict):
    def get_name(self, opcode):
        for key, value in self.items():
            if value == opcode:
                return key
        return f"UNKNOWN_{opcode}"


class _DummyWindowBackend:
    def __init__(self):
        self.net_state = [202]
        self.set_calls = []

    def get_property(self, name, _type=None, unpack=None):
        if name == "_NET_WM_STATE":
            return list(self.net_state)
        return []

    def set_property(self, name, value):
        self.set_calls.append((name, list(value)))
        if name == "_NET_WM_STATE":
            self.net_state = list(value)


class _DummyScreen:
    def __init__(self, name):
        self.name = name
        self.set_group_calls = []

    def set_group(self, group):
        self.set_group_calls.append(group.name)


class _DummyGroup:
    def __init__(self, name, screen):
        self.name = name
        self.screen = screen
        self.focus_calls = []

    def focus(self, win):
        self.focus_calls.append(id(win))


class _DummyConfig:
    def __init__(self):
        self.focus_on_window_activation = "never"
        self.auto_minimize = True


class _DummyQtile:
    def __init__(self, atoms, current_screen, groups):
        self.core = type("Core", (), {"conn": type("Conn", (), {"atoms": atoms})()})()
        self.current_screen = current_screen
        self.config = _DummyConfig()
        self.groups = groups


class DummyWindowHandleClientMessageProbe:
    handle_ClientMessage = Window.handle_ClientMessage

    def __init__(self):
        atoms = _DummyAtoms(
            {
                "_NET_WM_STATE": 101,
                "_NET_ACTIVE_WINDOW": 102,
                "_NET_CLOSE_WINDOW": 103,
                "WM_CHANGE_STATE": 104,
                "_NET_WM_DESKTOP": 105,
            }
        )

        self.current_screen = _DummyScreen("current")
        self.other_screen = _DummyScreen("other")
        self.group = _DummyGroup("g0", self.current_screen)
        groups = [_DummyGroup("g0", self.current_screen), _DummyGroup("g1", self.other_screen)]

        self.qtile = _DummyQtile(atoms=atoms, current_screen=self.current_screen, groups=groups)

        self.window = _DummyWindowBackend()
        self.urgent = False
        self.minimized = False

        self.kill_calls = 0
        self.bring_to_front_calls = 0
        self.togroup_calls = []

    def kill(self):
        self.kill_calls += 1

    def bring_to_front(self):
        self.bring_to_front_calls += 1

    def togroup(self, group_name=None, *, switch_group=False, toggle=False):
        self.togroup_calls.append((group_name, switch_group, toggle))


class TestBackendX11WindowDirectHandleClientMessageDefUsePairsQA:
    def test_backend_x11_window_direct_handle_client_message_def_use_pairs_case(self):
        probe = DummyWindowHandleClientMessageProbe()
        atoms = probe.qtile.core.conn.atoms

        hook_calls = []
        original_hook_fire = x11_window_mod.hook.fire
        x11_window_mod.hook.fire = lambda name, win: hook_calls.append((name, id(win)))

        try:
            probe.handle_ClientMessage(
                _DummyEvent(atoms["_NET_WM_STATE"], [x11_window_mod._NET_WM_STATE_ADD, 201, 202])
            )
            probe.handle_ClientMessage(
                _DummyEvent(atoms["_NET_WM_STATE"], [x11_window_mod._NET_WM_STATE_TOGGLE, 201, 0])
            )

            probe.handle_ClientMessage(_DummyEvent(atoms["_NET_ACTIVE_WINDOW"], [2, 0, 0]))

            probe.qtile.config.focus_on_window_activation = lambda win: True
            probe.handle_ClientMessage(_DummyEvent(atoms["_NET_ACTIVE_WINDOW"], [1, 0, 0]))

            probe.qtile.config.focus_on_window_activation = "smart"
            probe.group.screen = None
            probe.handle_ClientMessage(_DummyEvent(atoms["_NET_ACTIVE_WINDOW"], [1, 0, 0]))

            probe.group.screen = probe.current_screen
            probe.handle_ClientMessage(_DummyEvent(atoms["_NET_ACTIVE_WINDOW"], [1, 0, 0]))

            probe.group.screen = probe.other_screen
            probe.handle_ClientMessage(_DummyEvent(atoms["_NET_ACTIVE_WINDOW"], [1, 0, 0]))

            probe.qtile.config.focus_on_window_activation = "urgent"
            probe.handle_ClientMessage(_DummyEvent(atoms["_NET_ACTIVE_WINDOW"], [1, 0, 0]))

            probe.qtile.config.focus_on_window_activation = "never"
            probe.handle_ClientMessage(_DummyEvent(atoms["_NET_ACTIVE_WINDOW"], [1, 0, 0]))

            probe.qtile.config.focus_on_window_activation = 17
            probe.handle_ClientMessage(_DummyEvent(atoms["_NET_ACTIVE_WINDOW"], [1, 0, 0]))

            probe.handle_ClientMessage(_DummyEvent(atoms["_NET_CLOSE_WINDOW"], [0, 0, 0]))
            probe.handle_ClientMessage(_DummyEvent(atoms["WM_CHANGE_STATE"], [x11_window_mod.NormalState, 0, 0]))
            probe.handle_ClientMessage(_DummyEvent(atoms["WM_CHANGE_STATE"], [x11_window_mod.IconicState, 0, 0]))

            probe.handle_ClientMessage(_DummyEvent(atoms["_NET_WM_DESKTOP"], [1, 0, 0]))
            probe.handle_ClientMessage(_DummyEvent(atoms["_NET_WM_DESKTOP"], [99, 0, 0]))
            probe.handle_ClientMessage(_DummyEvent(atoms["_NET_WM_DESKTOP"], ["bad-index", 0, 0]))

            probe.handle_ClientMessage(_DummyEvent(999, [0, 0, 0]))
        finally:
            x11_window_mod.hook.fire = original_hook_fire

        assert probe.kill_calls == 1
        assert probe.bring_to_front_calls == 1
        assert probe.minimized is True
        assert probe.urgent is True
        assert len(probe.window.set_calls) == 2
        assert probe.current_screen.set_group_calls.count("g0") >= 3
        assert len(probe.group.focus_calls) >= 3
        assert ("g1", False, False) in probe.togroup_calls
        assert [name for name, _ in hook_calls].count("client_urgent_hint_changed") >= 2
