import libqtile.backend.x11.core as core_mod
from libqtile.backend.x11.core import Core


class _DummyMotionNotifyEvent:
    def __init__(self, kind):
        self.kind = kind


class _DummyEnterNotifyEvent:
    def __init__(self, kind):
        self.kind = kind


class _DummyButtonReleaseEvent:
    def __init__(self, kind):
        self.kind = kind


class _DummyPlainEvent:
    def __init__(self, kind):
        self.kind = kind


class _DummyWindowError(Exception):
    pass


class _DummyPictureError(Exception):
    pass


class _DummyConnRaw:
    def __init__(self, events, error_code=0):
        self.events = list(events)
        self.index = 0
        self.error_code = error_code

    def poll_for_event(self):
        if self.index >= len(self.events):
            return None
        event = self.events[self.index]
        self.index += 1
        return event

    def has_error(self):
        return self.error_code


class _DummyConn:
    def __init__(self, events, error_code=0):
        self.conn = _DummyConnRaw(events, error_code=error_code)


class _DummyQtile:
    def __init__(self):
        self.stop_calls = 0

    def stop(self):
        self.stop_calls += 1


class DummyCoreXpollProbe:
    _xpoll = Core._xpoll

    def __init__(self, events, error_code=0):
        self.qtile = _DummyQtile()
        self.conn = _DummyConn(events, error_code=error_code)
        self._motion_notify = None
        self.flush_calls = 0
        self.remove_listener_calls = 0
        self.handled_kinds = []

    def handle_event(self, event):
        self.handled_kinds.append(event.kind)
        if event.kind == "window_error":
            raise _DummyWindowError("synthetic window error")
        if event.kind == "generic_error":
            raise RuntimeError("synthetic generic error")

    def remove_listener(self):
        self.remove_listener_calls += 1

    def flush(self):
        self.flush_calls += 1


class TestBackendX11CoreDirectXpollDefUsePairsQA:
    def test_backend_x11_core_direct_xpoll_def_use_pairs_case(self):
        original_motion = core_mod.xcffib.xproto.MotionNotifyEvent
        original_enter = core_mod.xcffib.xproto.EnterNotifyEvent
        original_button_release = core_mod.xcffib.xproto.ButtonReleaseEvent
        original_window_error = core_mod.xcffib.xproto.WindowError
        original_picture_error = core_mod.xcffib.render.PictureError

        core_mod.xcffib.xproto.MotionNotifyEvent = _DummyMotionNotifyEvent
        core_mod.xcffib.xproto.EnterNotifyEvent = _DummyEnterNotifyEvent
        core_mod.xcffib.xproto.ButtonReleaseEvent = _DummyButtonReleaseEvent
        core_mod.xcffib.xproto.WindowError = _DummyWindowError
        core_mod.xcffib.render.PictureError = _DummyPictureError

        try:
            events = [
                _DummyMotionNotifyEvent("motion_1"),
                _DummyEnterNotifyEvent("enter_1"),
                _DummyMotionNotifyEvent("motion_2"),
                _DummyPlainEvent("window_error"),
                _DummyButtonReleaseEvent("button_release"),
                _DummyPlainEvent("generic_error"),
                _DummyMotionNotifyEvent("motion_3"),
            ]
            probe = DummyCoreXpollProbe(events=events, error_code=0)
            probe._xpoll()
        finally:
            core_mod.xcffib.xproto.MotionNotifyEvent = original_motion
            core_mod.xcffib.xproto.EnterNotifyEvent = original_enter
            core_mod.xcffib.xproto.ButtonReleaseEvent = original_button_release
            core_mod.xcffib.xproto.WindowError = original_window_error
            core_mod.xcffib.render.PictureError = original_picture_error

        assert probe.handled_kinds == [
            "motion_1",
            "enter_1",
            "window_error",
            "motion_2",
            "button_release",
            "generic_error",
            "motion_3",
        ]
        assert probe._motion_notify is None
        assert probe.flush_calls == 1
        assert probe.remove_listener_calls == 0
        assert probe.qtile.stop_calls == 0
