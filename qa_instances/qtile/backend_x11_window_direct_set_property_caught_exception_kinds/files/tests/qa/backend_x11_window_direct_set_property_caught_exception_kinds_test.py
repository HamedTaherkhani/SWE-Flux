from libqtile.backend.x11 import window as x11_window
from libqtile.backend.x11.window import XWindow


class _DummyWindowError(Exception):
    pass


class _DummyCheckResult:
    def __init__(self, should_raise: bool):
        self.should_raise = should_raise

    def check(self):
        if self.should_raise:
            raise _DummyWindowError("synthetic window error during check")


class _DummyCore:
    def __init__(self):
        self.change_calls = []

    def ChangePropertyChecked(self, mode, wid, name_atom, type_atom, fmt, value_len, value):
        self.change_calls.append(
            {
                "mode": mode,
                "wid": wid,
                "name_atom": name_atom,
                "type_atom": type_atom,
                "fmt": fmt,
                "value_len": value_len,
                "value": value,
            }
        )
        # Force only the final call to hit the caught WindowError branch.
        return _DummyCheckResult(should_raise=(len(self.change_calls) == 3))


class _DummyConnWrapper:
    def __init__(self):
        self.core = _DummyCore()


class _DummyAtoms(dict):
    def __getitem__(self, key):
        if key not in self:
            self[key] = abs(hash(key)) % 100000 + 1
        return dict.__getitem__(self, key)


class _DummyConn:
    def __init__(self):
        self.conn = _DummyConnWrapper()
        self.atoms = _DummyAtoms()


class TestBackendX11WindowDirectSetPropertyCaughtExceptionKindsQA:
    def test_backend_x11_window_direct_set_property_caught_exception_kinds_case(self):
        win = XWindow(_DummyConn(), wid=77)

        original_window_error = x11_window.xcffib.xproto.WindowError
        x11_window.xcffib.xproto.WindowError = _DummyWindowError
        try:
            # Triggers internal `except StopIteration` path.
            win.set_property("_NET_WM_NAME", [])
            # Triggers internal `except TypeError` path.
            win.set_property("_NET_WM_NAME", 12345)
            # Triggers internal `except WindowError` path in checked property update.
            win.set_property("_NET_WM_NAME", [1, 2, 3, 5, 8])
        finally:
            x11_window.xcffib.xproto.WindowError = original_window_error

        calls = win.conn.conn.core.change_calls
        assert len(calls) == 3
        assert calls[0]["value_len"] == 0
        assert calls[1]["value_len"] == 1
        assert calls[2]["value_len"] == 5
