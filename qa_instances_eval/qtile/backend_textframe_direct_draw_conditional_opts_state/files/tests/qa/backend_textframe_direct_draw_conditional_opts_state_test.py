from libqtile.backend.base.drawer import TextFrame


class DummyContext:
    def __init__(self):
        self.stroke_calls = 0

    def stroke(self):
        self.stroke_calls += 1


class DummyDrawer:
    def __init__(self):
        self.ctx = DummyContext()
        self.fillrect_calls = []
        self.rounded_fillrect_calls = []
        self.rounded_rectangle_calls = []
        self.rectangle_calls = []
        self.set_source_rgb_calls = []

    def set_source_rgb(self, color):
        self.set_source_rgb_calls.append(color)

    def fillrect(self, *args):
        self.fillrect_calls.append(args)

    def rounded_fillrect(self, *args):
        self.rounded_fillrect_calls.append(args)

    def rounded_rectangle(self, *args):
        self.rounded_rectangle_calls.append(args)

    def rectangle(self, *args):
        self.rectangle_calls.append(args)


class DummyLayout:
    def __init__(self):
        self.drawer = DummyDrawer()
        self.width = 173
        self.height = 59
        self.draw_calls = []

    def draw(self, x, y):
        self.draw_calls.append((x, y))


class TestBackendTextFrameDirectDrawConditionalOptsStateQA:
    def test_backend_textframe_direct_draw_conditional_opts_state_case(self):
        layout = DummyLayout()
        frame = TextFrame(
            layout=layout,
            border_width=7,
            border_color="#aabbcc",
            pad_x=(11, 4),
            pad_y=(8, 5),
            highlight_color="#334455",
        )

        # Warm-up branches to make control flow less obvious.
        frame.draw(12, 6, rounded=True, fill=True, line=False, highlight=False)
        frame.draw(31, 14, rounded=False, fill=False, line=True, highlight=False)

        # Target branch: nested conditional where `opts` is mutated in `line` path.
        frame.draw(37, 23, rounded=False, fill=False, line=True, highlight=True)

        assert layout.drawer.ctx.stroke_calls == 3
        assert layout.drawer.fillrect_calls[-1] == (37, 65, 188, 7, 7)
        assert layout.draw_calls[-1] == (48, 31)
