from types import SimpleNamespace

import libqtile.backend.x11.core as x11_core_mod
import libqtile.backend.x11.window as x11_window_mod
from libqtile.backend.x11.core import Core as XCore
from libqtile.backend.x11.window import XWindow


class MotionNotifyEvent:
    pass


class EnterNotifyEvent:
    pass


class LeaveNotifyEvent:
    pass


class ButtonPressEvent:
    pass


class GenericNotifyEvent:
    pass


class _DummyAccessError(Exception):
    pass


class _DummyWindowError(Exception):
    pass


class _DummyValue:
    def __init__(self, atoms):
        self._atoms = list(atoms)

    def to_atoms(self):
        return tuple(self._atoms)


class _DummyPropertyReply:
    def __init__(self, atoms):
        self.value = _DummyValue(atoms)
        self.value_len = len(atoms)


class _DummyPropertyCookie:
    def __init__(self, mode, payload):
        self.mode = mode
        self.payload = payload

    def reply(self):
        if self.mode == "error":
            raise self.payload
        return _DummyPropertyReply(self.payload)


class _DummyXWindowCore:
    def __init__(self):
        # Mixed outcomes: valid type lookup, backend access error, empty property,
        # known/unknown atom names. This makes the path difficult to infer statically.
        self.operations = [
            ("atoms", [9101, 9102]),
            ("error", _DummyAccessError("synthetic access error")),
            ("atoms", [9103]),
            ("atoms", []),
            ("atoms", [9104, 9105]),
            ("error", _DummyAccessError("synthetic access error")),
            ("atoms", [9106]),
            ("atoms", [9107, 9108]),
            ("atoms", []),
            ("atoms", [9109]),
        ]
        self.calls = 0

    def GetProperty(self, *_args):
        if self.calls < len(self.operations):
            mode, payload = self.operations[self.calls]
        else:
            mode, payload = ("atoms", [9109])
        self.calls += 1
        return _DummyPropertyCookie(mode, payload)


class _DummyAtoms(dict):
    def __init__(self):
        super().__init__()
        self.names = {
            9101: "_NET_WM_WINDOW_TYPE_FAKE_A",
            9102: "_NET_WM_WINDOW_TYPE_DIALOG",
            9103: "_NET_WM_WINDOW_TYPE_FAKE_B",
            9104: "_NET_WM_WINDOW_TYPE_FAKE_C",
            9105: "_NET_WM_WINDOW_TYPE_SPLASH",
            9106: "_NET_WM_WINDOW_TYPE_NORMAL",
            9107: "_NET_WM_WINDOW_TYPE_FAKE_D",
            9108: "_NET_WM_WINDOW_TYPE_FAKE_E",
            9109: "_NET_WM_WINDOW_TYPE_DIALOG",
        }

    def __getitem__(self, key):
        if key not in self:
            self[key] = abs(hash(key)) % 100000 + 1
        return dict.__getitem__(self, key)

    def get_name(self, atom_id: int):
        return self.names.get(atom_id, f"UNKNOWN_{atom_id}")


class _DummyXWindowConn:
    def __init__(self):
        self.conn = SimpleNamespace(core=_DummyXWindowCore())
        self.atoms = _DummyAtoms()


class _DummyEventConn:
    def __init__(self, events):
        self.events = list(events)

    def poll_for_event(self):
        if self.events:
            return self.events.pop(0)
        return None

    def has_error(self):
        return 0


class DummyBackendX11CoreProbe:
    _xpoll = XCore._xpoll
    handle_event = XCore.handle_event

    def __init__(self):
        self.qtile = object()
        self._motion_notify = None
        self.flush_calls = 0

        events = [
            MotionNotifyEvent(),
            EnterNotifyEvent(),
            LeaveNotifyEvent(),
            MotionNotifyEvent(),
            ButtonPressEvent(),
            GenericNotifyEvent(),
        ]
        self.conn = SimpleNamespace(conn=_DummyEventConn(events))

        self.xwindow = XWindow(_DummyXWindowConn(), wid=77)
        self.handler_trace = []

    def _get_target_chain(self, event_type: str, _event):
        if event_type in {"MotionNotify", "EnterNotify", "LeaveNotify", "ButtonPress"}:
            return [self._target_primary, self._target_secondary]
        return [self._target_secondary]

    def _target_primary(self, event):
        wm_type = self.xwindow.get_wm_type()
        self.handler_trace.append(("primary", event.__class__.__name__, wm_type))
        return event.__class__.__name__ != "ButtonPressEvent"

    def _target_secondary(self, event):
        wm_type = self.xwindow.get_wm_type()
        self.handler_trace.append(("secondary", event.__class__.__name__, wm_type))
        return True

    def flush(self):
        self.flush_calls += 1


class TestBackendX11CorePollMultiFileExecutionPathLinesQA:
    def test_backend_x11_core_poll_multi_file_execution_path_lines_case(self):
        probe = DummyBackendX11CoreProbe()

        orig_motion = x11_core_mod.xcffib.xproto.MotionNotifyEvent
        orig_enter = x11_core_mod.xcffib.xproto.EnterNotifyEvent
        orig_leave = x11_core_mod.xcffib.xproto.LeaveNotifyEvent
        orig_press = x11_core_mod.xcffib.xproto.ButtonPressEvent

        orig_access = x11_window_mod.xcffib.xproto.AccessError
        orig_window = x11_window_mod.xcffib.xproto.WindowError

        x11_core_mod.xcffib.xproto.MotionNotifyEvent = MotionNotifyEvent
        x11_core_mod.xcffib.xproto.EnterNotifyEvent = EnterNotifyEvent
        x11_core_mod.xcffib.xproto.LeaveNotifyEvent = LeaveNotifyEvent
        x11_core_mod.xcffib.xproto.ButtonPressEvent = ButtonPressEvent

        x11_window_mod.xcffib.xproto.AccessError = _DummyAccessError
        x11_window_mod.xcffib.xproto.WindowError = _DummyWindowError

        try:
            probe._xpoll()
        finally:
            x11_core_mod.xcffib.xproto.MotionNotifyEvent = orig_motion
            x11_core_mod.xcffib.xproto.EnterNotifyEvent = orig_enter
            x11_core_mod.xcffib.xproto.LeaveNotifyEvent = orig_leave
            x11_core_mod.xcffib.xproto.ButtonPressEvent = orig_press

            x11_window_mod.xcffib.xproto.AccessError = orig_access
            x11_window_mod.xcffib.xproto.WindowError = orig_window

        # Six logical events handled, with one chain break at ButtonPress.
        assert len(probe.handler_trace) == 10
        assert probe.flush_calls == 1
        assert [t[0] for t in probe.handler_trace].count("primary") == 5
        assert [t[0] for t in probe.handler_trace].count("secondary") == 5
        assert any(item[2] == "dialog" for item in probe.handler_trace)
        assert any(item[2] is None for item in probe.handler_trace)
