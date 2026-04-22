from __future__ import annotations

from types import SimpleNamespace

import pytest

from libqtile.backend.x11 import core as core_mod
from libqtile.backend.x11.core import Core


class FakeMotionNotifyEvent:
    pass


class FakeEnterNotifyEvent:
    pass


class FakeLeaveNotifyEvent:
    pass


class FakeButtonPressEvent:
    pass


class FakeButtonReleaseEvent:
    pass


class FakeIgnoredEvent:
    pass


class FakeRegularEvent:
    pass


class FakeWindowError(Exception):
    pass


class FakeAccessError(Exception):
    pass


class FakeDrawableError(Exception):
    pass


class FakeGContextError(Exception):
    pass


class FakePixmapError(Exception):
    pass


class FakePictureError(Exception):
    pass


FAKE_XPROTO = SimpleNamespace(
    MotionNotifyEvent=FakeMotionNotifyEvent,
    EnterNotifyEvent=FakeEnterNotifyEvent,
    LeaveNotifyEvent=FakeLeaveNotifyEvent,
    ButtonPressEvent=FakeButtonPressEvent,
    ButtonReleaseEvent=FakeButtonReleaseEvent,
    WindowError=FakeWindowError,
    AccessError=FakeAccessError,
    DrawableError=FakeDrawableError,
    GContextError=FakeGContextError,
    PixmapError=FakePixmapError,
)

FAKE_XCFFIB = SimpleNamespace(
    xproto=FAKE_XPROTO,
    render=SimpleNamespace(PictureError=FakePictureError),
)


class DummyRawConn:
    def __init__(self, items, has_error=0):
        self.items = list(items)
        self._has_error = has_error
        self.has_error_calls = 0

    def poll_for_event(self):
        if not self.items:
            return None

        item = self.items.pop(0)
        if isinstance(item, BaseException):
            raise item

        return item

    def has_error(self):
        self.has_error_calls += 1
        return self._has_error


class DummyConn:
    def __init__(self, raw_conn):
        self.conn = raw_conn


class DummyQtile:
    def __init__(self):
        self.stop_calls = 0

    def stop(self):
        self.stop_calls += 1


class DummyXPollProbe:
    _xpoll = Core._xpoll

    def __init__(self, raw_conn):
        self.qtile = DummyQtile()
        self.conn = DummyConn(raw_conn)
        self._motion_notify = None
        self.handled = []
        self.flush_calls = 0
        self.remove_listener_calls = 0

    def handle_event(self, event):
        self.handled.append(type(event).__name__)

    def flush(self):
        self.flush_calls += 1

    def remove_listener(self):
        self.remove_listener_calls += 1


CASES = [
    {
        "name": "empty_queue_flushes",
        "queue": [],
        "has_error": 0,
        "handled": [],
        "flush_calls": 1,
        "remove_listener_calls": 0,
        "stop_calls": 0,
        "warning_calls": 0,
        "exception_calls": 0,
    },
    {
        "name": "ignored_event_skipped",
        "queue": [FakeIgnoredEvent()],
        "has_error": 0,
        "handled": [],
        "flush_calls": 1,
        "remove_listener_calls": 0,
        "stop_calls": 0,
        "warning_calls": 0,
        "exception_calls": 0,
    },
    {
        "name": "motion_then_enter_handles_motion_first",
        "queue": [FakeMotionNotifyEvent(), FakeEnterNotifyEvent()],
        "has_error": 0,
        "handled": ["FakeMotionNotifyEvent", "FakeEnterNotifyEvent"],
        "flush_calls": 1,
        "remove_listener_calls": 0,
        "stop_calls": 0,
        "warning_calls": 0,
        "exception_calls": 0,
    },
    {
        "name": "motion_deferred_until_loop_end",
        "queue": [FakeMotionNotifyEvent(), FakeRegularEvent()],
        "has_error": 0,
        "handled": ["FakeRegularEvent", "FakeMotionNotifyEvent"],
        "flush_calls": 1,
        "remove_listener_calls": 0,
        "stop_calls": 0,
        "warning_calls": 0,
        "exception_calls": 0,
    },
    {
        "name": "motion_then_buttonpress_priority",
        "queue": [FakeMotionNotifyEvent(), FakeButtonPressEvent()],
        "has_error": 0,
        "handled": ["FakeMotionNotifyEvent", "FakeButtonPressEvent"],
        "flush_calls": 1,
        "remove_listener_calls": 0,
        "stop_calls": 0,
        "warning_calls": 0,
        "exception_calls": 0,
    },
    {
        "name": "xproto_window_error_ignored",
        "queue": [FakeWindowError("werr"), FakeRegularEvent()],
        "has_error": 0,
        "handled": ["FakeRegularEvent"],
        "flush_calls": 1,
        "remove_listener_calls": 0,
        "stop_calls": 0,
        "warning_calls": 0,
        "exception_calls": 0,
    },
    {
        "name": "render_picture_error_ignored",
        "queue": [FakePictureError("perr"), FakeRegularEvent()],
        "has_error": 0,
        "handled": ["FakeRegularEvent"],
        "flush_calls": 1,
        "remove_listener_calls": 0,
        "stop_calls": 0,
        "warning_calls": 0,
        "exception_calls": 0,
    },
    {
        "name": "generic_exception_without_disconnect",
        "queue": [RuntimeError("boom"), FakeRegularEvent()],
        "has_error": 0,
        "handled": ["FakeRegularEvent"],
        "flush_calls": 1,
        "remove_listener_calls": 0,
        "stop_calls": 0,
        "warning_calls": 0,
        "exception_calls": 1,
    },
    {
        "name": "generic_exception_disconnects",
        "queue": [RuntimeError("disconnect")],
        "has_error": 9,
        "handled": [],
        "flush_calls": 0,
        "remove_listener_calls": 1,
        "stop_calls": 1,
        "warning_calls": 1,
        "exception_calls": 0,
    },
    {
        "name": "pending_motion_flush_after_ignored",
        "queue": [FakeMotionNotifyEvent(), FakeIgnoredEvent()],
        "has_error": 0,
        "handled": ["FakeMotionNotifyEvent"],
        "flush_calls": 1,
        "remove_listener_calls": 0,
        "stop_calls": 0,
        "warning_calls": 0,
        "exception_calls": 0,
    },
    {
        "name": "enter_without_pending_motion",
        "queue": [FakeEnterNotifyEvent()],
        "has_error": 0,
        "handled": ["FakeEnterNotifyEvent"],
        "flush_calls": 1,
        "remove_listener_calls": 0,
        "stop_calls": 0,
        "warning_calls": 0,
        "exception_calls": 0,
    },
]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
class TestBackendX11CoreDirectXpollLineCoverageSuiteQA:
    def test_backend_x11_core_direct_xpoll_line_coverage_suite_case(self, case, monkeypatch):
        warning_calls = []
        exception_calls = []

        monkeypatch.setattr(core_mod, "xcffib", FAKE_XCFFIB)
        monkeypatch.setattr(core_mod, "_IGNORED_EVENTS", {FakeIgnoredEvent})
        monkeypatch.setattr(core_mod.logger, "warning", lambda *a, **k: warning_calls.append((a, k)))
        monkeypatch.setattr(core_mod.logger, "exception", lambda *a, **k: exception_calls.append((a, k)))

        raw_conn = DummyRawConn(case["queue"], has_error=case["has_error"])
        probe = DummyXPollProbe(raw_conn)

        probe._xpoll()

        assert probe.handled == case["handled"]
        assert probe.flush_calls == case["flush_calls"]
        assert probe.remove_listener_calls == case["remove_listener_calls"]
        assert probe.qtile.stop_calls == case["stop_calls"]

        if case["exception_calls"] == 0:
            assert len(exception_calls) == 0
        else:
            assert len(exception_calls) >= case["exception_calls"]

        if case["warning_calls"] == 0:
            assert len(warning_calls) == 0
        else:
            assert len(warning_calls) >= case["warning_calls"]

        if case["name"] == "generic_exception_disconnects":
            assert raw_conn.has_error_calls == 1
        else:
            assert raw_conn.has_error_calls in (0, 1)
