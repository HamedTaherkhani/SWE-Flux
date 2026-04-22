from libqtile.backend.x11 import xcbq


class _DummyReply:
    def __init__(self, payload):
        self.payload = payload

    def reply(self):
        return self.payload


class _DummyCore:
    def __init__(self):
        self.named_calls = []
        self.rgb_calls = []

    def AllocNamedColor(self, cid, name_len, color):
        self.named_calls.append((cid, name_len, color))
        if color == "steelblue":
            return _DummyReply(("named", cid, name_len, color))
        raise NameError("synthetic unknown color")

    def AllocColor(self, cid, r, g, b):
        self.rgb_calls.append((cid, r, g, b))
        return _DummyReply(("rgb", cid, r, g, b))


class _DummyConnWrapper:
    def __init__(self):
        self.core = _DummyCore()


class _DummyConn:
    def __init__(self):
        self.conn = _DummyConnWrapper()


class _BadHexColor:
    def __len__(self):
        return 11

    def __index__(self):
        raise ValueError("cannot convert to hex")


class TestBackendX11ColormapDirectAllocColorCaughtExceptionKindsQA:
    def test_backend_x11_colormap_direct_alloc_color_caught_exception_kinds_case(self):
        colormap = xcbq.Colormap(_DummyConn(), cid=41)

        # Force the test to use a controllable exception type in this environment.
        original_name_error = xcbq.xcffib.xproto.NameError
        xcbq.xcffib.xproto.NameError = NameError
        try:
            out_fallback = colormap.alloc_color(_BadHexColor())
            out_rgb_tuple = colormap.alloc_color((18, 52, 86))
            out_named = colormap.alloc_color("steelblue")
        finally:
            xcbq.xcffib.xproto.NameError = original_name_error

        assert out_fallback == ("rgb", 41, 65535, 0, 0)
        assert out_rgb_tuple == ("rgb", 41, 4626, 13364, 22102)
        assert out_named == ("named", 41, 9, "steelblue")
        assert len(colormap.conn.conn.core.named_calls) == 3
        assert len(colormap.conn.conn.core.rgb_calls) == 2
