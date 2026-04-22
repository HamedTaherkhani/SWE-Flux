from libqtile.backend.base import FloatStates
from libqtile.backend.x11.window import XWindow, _Window


class DummyCheckedRequest:
    def check(self):
        return None


class DummyCore:
    def __init__(self):
        self.calls = []

    def ConfigureWindow(self, wid, mask, values):
        self.calls.append(("ConfigureWindow", wid, mask, list(values)))
        return None

    def ChangePropertyChecked(self, mode, wid, prop, _type, fmt, length, value):
        self.calls.append(("ChangePropertyChecked", mode, wid, prop, _type, fmt, length, list(value)))
        return DummyCheckedRequest()

    def CreatePixmap(self, depth, pixmap, wid, width, height):
        self.calls.append(("CreatePixmap", depth, pixmap, wid, width, height))

    def CreateGC(self, gc, pixmap, mask, values):
        self.calls.append(("CreateGC", gc, pixmap, mask, values))

    def ChangeGC(self, gc, mask, values):
        self.calls.append(("ChangeGC", gc, mask, list(values)))

    def PolyFillRectangle(self, pixmap, gc, count, rects):
        self.calls.append(("PolyFillRectangle", pixmap, gc, count, len(rects)))

    def CopyArea(self, src, dst, gc, src_x, src_y, dst_x, dst_y, width, height):
        self.calls.append(("CopyArea", src, dst, gc, src_x, src_y, dst_x, dst_y, width, height))

    def ChangeWindowAttributes(self, wid, mask, values):
        self.calls.append(("ChangeWindowAttributes", wid, mask, list(values)))

    def SendEvent(self, propagate, wid, mask, packed):
        self.calls.append(("SendEvent", propagate, wid, mask, len(packed)))

    def FreePixmap(self, pixmap):
        self.calls.append(("FreePixmap", pixmap))

    def FreeGC(self, gc):
        self.calls.append(("FreeGC", gc))


class DummyRawConn:
    def __init__(self):
        self.core = DummyCore()
        self._next_id = 4000

    def generate_id(self):
        self._next_id += 1
        return self._next_id


class DummyAtoms(dict):
    def __init__(self):
        super().__init__()
        self.reverse = {}
        self._next = 100

    def __getitem__(self, key):
        if isinstance(key, int):
            return key
        if key not in self:
            self._next += 1
            value = self._next
            dict.__setitem__(self, key, value)
            self.reverse[value] = key
        return dict.__getitem__(self, key)

    def get_name(self, atom_id):
        return self.reverse.get(atom_id, f"ATOM_{atom_id}")


class DummyXConn:
    def __init__(self):
        self.conn = DummyRawConn()
        self.atoms = DummyAtoms()

    def color_pixel(self, color: str):
        return (sum(ord(ch) for ch in color) * 17) & 0xFFFFFF


class DummyScreen:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y


class DummyGroup:
    def __init__(self, screen):
        self.screen = screen


class DummyWindowPlaceProbe:
    place = _Window.place
    paint_borders = _Window.paint_borders
    send_configure_notify = _Window.send_configure_notify

    def __init__(self):
        self.conn = DummyXConn()
        self.window = XWindow(self.conn, wid=901)
        self.wid = 901

        self.group = DummyGroup(DummyScreen(37, 19))
        self.x = 0
        self.y = 0
        self.width = 640
        self.height = 480
        self.depth = 24

        self.borderwidth = 0
        self.bordercolor = None

        self._float_state = FloatStates.FLOATING
        self.fullscreen = True

        self.hints = {
            "flags": {"PMinSize", "PMaxSize", "PAspect"},
            "min_width": 210,
            "min_height": 140,
            "max_width": 840,
            "max_height": 610,
            "min_aspect": (4, 3),
            "max_aspect": (16, 9),
            "base_width": 120,
            "base_height": 90,
            "width_inc": 13,
            "height_inc": 11,
        }


class TestBackendX11WindowDirectPlaceMaxCallDepthQA:
    def test_backend_x11_window_direct_place_max_call_depth_case(self):
        probe = DummyWindowPlaceProbe()

        # Warm-up call with integer margin and no hints.
        probe.place(
            x=213,
            y=147,
            width=672,
            height=395,
            borderwidth=3,
            bordercolor=["#445566", "#778899", "#aabbcc"],
            above=False,
            margin=5,
            respect_hints=False,
        )

        # Target call with list margin and full hints path.
        probe.place(
            x=321,
            y=203,
            width=917,
            height=581,
            borderwidth=6,
            bordercolor=["#112233", "#335577", "#557799", "#7799bb"],
            above=False,
            margin=[7, 9, 11, 13],
            respect_hints=True,
        )

        assert (probe.x, probe.y, probe.width, probe.height) == (336, 210, 835, 563)
        assert (probe.float_x, probe.float_y) == (299, 191)
        assert probe.borderwidth == 6
        assert len([c for c in probe.conn.conn.core.calls if c[0] == "ConfigureWindow"]) >= 4
        assert len([c for c in probe.conn.conn.core.calls if c[0] == "CopyArea"]) >= 8
        assert any(c[0] == "SendEvent" for c in probe.conn.conn.core.calls)
