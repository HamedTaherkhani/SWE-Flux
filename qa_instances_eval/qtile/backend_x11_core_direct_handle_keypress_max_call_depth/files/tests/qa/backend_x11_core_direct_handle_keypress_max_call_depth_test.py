import libqtile.backend.x11.core as core_mod
from libqtile.backend.x11.core import Core


class DummyKey:
    def __init__(self, key, modifiers):
        self.key = key
        self.modifiers = modifiers


class DummyCoreConnCore:
    def __init__(self):
        self.grab_calls = []
        self.ungrab_calls = []

    def GrabKey(self, owner_events, root, modmask, code, mode1, mode2):
        self.grab_calls.append((owner_events, root, modmask, code, mode1, mode2))

    def UngrabKey(self, code, root, modmask):
        self.ungrab_calls.append((code, root, modmask))


class DummyConn:
    def __init__(self):
        self.conn = type("Raw", (), {"core": DummyCoreConnCore()})()
        self.code_to_syms = {
            24: [core_mod.xcbq.keysyms["a"]],
            38: [core_mod.xcbq.keysyms["b"]],
            39: [core_mod.xcbq.keysyms["s"]],
        }
        self.flush_calls = 0

    def keysym_to_keycode(self, keysym):
        if keysym == core_mod.xcbq.keysyms["a"]:
            return [0, 24, 38]
        if keysym == core_mod.xcbq.keysyms["b"]:
            return [38, 56]
        return [39]

    def flush(self):
        self.flush_calls += 1


class DummyXTest:
    def __init__(self):
        self.fake_input_calls = []

    def FakeInput(self, input_type, detail, delay, xid, x, y, device):
        self.fake_input_calls.append((input_type, detail, delay, xid, x, y, device))


class DummyQtile:
    def __init__(self):
        self.calls = []
        self.key_a = DummyKey("a", ["control", "mod1"]) 
        self.key_b = DummyKey("b", ["shift", "mod4"]) 

    def process_key_event(self, keysym, masked_state):
        self.calls.append((keysym, masked_state))

        if keysym == core_mod.xcbq.keysyms["a"]:
            return self.key_a, False
        if keysym == core_mod.xcbq.keysyms["b"]:
            return self.key_b, False
        return None, True


class DummyEvent:
    def __init__(self, detail: int, state: int):
        self.detail = detail
        self.state = state


class DummyCoreHandleKeyPressProbe:
    handle_KeyPress = Core.handle_KeyPress
    ungrab_key = Core.ungrab_key
    grab_key = Core.grab_key
    lookup_key = Core.lookup_key
    _auto_modmasks = Core._auto_modmasks
    _fake_KeyPress = Core._fake_KeyPress
    _fake_input = Core._fake_input
    flush = Core.flush

    def __init__(self):
        self.conn = DummyConn()
        self._root = type("Root", (), {"wid": 7001})()
        self._valid_mask = 0xFF
        self._numlock_mask = 0x10
        self._xtest = DummyXTest()
        self.qtile = DummyQtile()


class TestBackendX11CoreDirectHandleKeyPressMaxCallDepthQA:
    def test_backend_x11_core_direct_handle_keypress_max_call_depth_case(self):
        probe = DummyCoreHandleKeyPressProbe()

        probe.handle_KeyPress(DummyEvent(detail=24, state=0x1F3), simulated=False)
        probe.handle_KeyPress(DummyEvent(detail=38, state=0x2B7), simulated=False)
        probe.handle_KeyPress(DummyEvent(detail=39, state=0x00F), simulated=True)

        assert len(probe.qtile.calls) == 3
        assert len(probe.conn.conn.core.ungrab_calls) > 10
        assert len(probe.conn.conn.core.grab_calls) > 10
        assert len(probe._xtest.fake_input_calls) == 6
        assert probe.conn.flush_calls == 6
