from libqtile.widget.groupbox import GroupBox


class _DummyWindow:
    def __init__(self, urgent=False):
        self.urgent = urgent


class _DummyGroup:
    def __init__(self, name, label, windows=None, screen=None):
        self.name = name
        self.label = label
        self.windows = windows or []
        self.screen = screen


class _DummyScreen:
    def __init__(self):
        self.group = None


class _DummyDrawer:
    def __init__(self):
        self.clear_calls = []
        self.draw_calls = []

    def clear(self, color):
        self.clear_calls.append(color)

    def draw(self, *, offsetx, offsety, width):
        self.draw_calls.append((offsetx, offsety, width))


class _DummyBar:
    def __init__(self, screen, background="#101010"):
        self.background = background
        self.screen = screen


class _DummyQtile:
    def __init__(self, current_screen):
        self.current_screen = current_screen


class DummyGroupBoxDrawProbe:
    draw = GroupBox.draw
    group_has_urgent = GroupBox.group_has_urgent

    def __init__(self, groups, bar_screen, other_screen):
        self.groups = groups
        self.drawer = _DummyDrawer()
        self.bar = _DummyBar(bar_screen, background="#222222")
        self.qtile = _DummyQtile(current_screen=bar_screen)

        self.background = None
        self.margin_x = 6
        self.spacing = 4

        self.highlight_method = "line"
        self.urgent_alert_method = "border"

        self.urgent_text = "#ff0000"
        self.active = "#00ff00"
        self.inactive = "#888888"

        self.block_highlight_text_color = "#ffee00"
        self.this_current_screen_border = "#1111ff"
        self.this_screen_border = "#00aaaa"
        self.other_current_screen_border = "#ff11ff"
        self.other_screen_border = "#ffaa11"
        self.urgent_border = "#ff6600"

        self.highlight_color = ["#101010", "#202020"]
        self.rounded = True

        self.offset = 3
        self.offsety = 2
        self.width = 420

        self._other_screen = other_screen
        self.drawbox_calls = []

    def box_width(self, groups):
        return 18 + sum(len(g.label) * 7 for g in groups)

    def drawbox(
        self,
        offset,
        label,
        border,
        text_color,
        *,
        highlight_color,
        width,
        rounded,
        block,
        line,
        highlighted,
    ):
        self.drawbox_calls.append(
            {
                "offset": offset,
                "label": label,
                "border": border,
                "text_color": text_color,
                "highlight_color": highlight_color,
                "width": width,
                "rounded": rounded,
                "block": block,
                "line": line,
                "highlighted": highlighted,
            }
        )


class TestWidgetGroupBoxDirectDrawDefUsePairsQA:
    def test_widget_groupbox_direct_draw_def_use_pairs_case(self):
        screen_main = _DummyScreen()
        screen_other = _DummyScreen()

        g_urgent = _DummyGroup("u", "URG", windows=[_DummyWindow(urgent=True)], screen=None)
        g_main = _DummyGroup("m", "MAIN", windows=[_DummyWindow(urgent=False)], screen=screen_main)
        g_other = _DummyGroup("o", "OTHER", windows=[_DummyWindow(urgent=False)], screen=screen_other)
        g_empty = _DummyGroup("e", "EMPTY", windows=[], screen=None)

        screen_main.group = g_main
        screen_other.group = g_other

        probe = DummyGroupBoxDrawProbe(
            groups=[g_urgent, g_main, g_other, g_empty],
            bar_screen=screen_main,
            other_screen=screen_other,
        )

        probe.draw()

        probe.highlight_method = "text"
        probe.urgent_alert_method = "text"
        probe.qtile.current_screen = screen_other

        probe.draw()

        assert len(probe.drawer.clear_calls) == 2
        assert len(probe.drawer.draw_calls) == 2
        assert len(probe.drawbox_calls) == 8

        assert any(call["border"] == probe.urgent_border for call in probe.drawbox_calls)
        assert any(call["highlighted"] for call in probe.drawbox_calls)
        assert any(call["text_color"] == probe.urgent_text for call in probe.drawbox_calls)
        assert any(call["line"] for call in probe.drawbox_calls)
