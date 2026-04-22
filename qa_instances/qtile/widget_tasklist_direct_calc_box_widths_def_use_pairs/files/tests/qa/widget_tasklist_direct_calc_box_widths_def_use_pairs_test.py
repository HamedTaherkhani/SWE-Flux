from libqtile.widget.tasklist import TaskList


class _DummyWindow:
    def __init__(self, wid, name):
        self.wid = wid
        self.name = name


class _DummyIcon:
    pass


class DummyTaskListCalcBoxWidthsProbe:
    calc_box_widths = TaskList.calc_box_widths

    def __init__(self):
        self.windows = []
        self.margin_x = 6
        self.spacing = 4
        self.padding_x = 5

        self.max_width = 220
        self.icon_size = 0
        self.title_width_method = None
        self.max_title_width = None

        self._icon_map = {}

    def get_taskname(self, window):
        return window.name

    def get_window_icon(self, window):
        return self._icon_map.get(window.wid)

    def box_width(self, task_name):
        return len(task_name) * 11 + 5


class TestWidgetTaskListDirectCalcBoxWidthsDefUsePairsQA:
    def test_widget_tasklist_direct_calc_box_widths_def_use_pairs_case(self):
        probe = DummyTaskListCalcBoxWidthsProbe()

        empty_case = probe.calc_box_widths()
        assert empty_case == []

        probe.windows = [
            _DummyWindow(1, "alpha"),
            _DummyWindow(2, "beta"),
            _DummyWindow(3, "gamma"),
            _DummyWindow(4, "delta"),
        ]
        probe.title_width_method = "uniform"
        probe.icon_size = 0
        probe.max_width = 240
        probe.max_title_width = None

        uniform_rows = list(probe.calc_box_widths())
        uniform_widths = [row[3] for row in uniform_rows]

        assert len(uniform_rows) == 4
        assert len(set(uniform_widths)) == 1

        probe.windows = [
            _DummyWindow(10, "very-long-window-alpha"),
            _DummyWindow(11, "mid-window-beta"),
            _DummyWindow(12, "tiny"),
        ]
        probe.title_width_method = None
        probe.icon_size = 16
        probe.max_width = 130
        probe.max_title_width = 90
        probe._icon_map = {10: _DummyIcon(), 11: _DummyIcon(), 12: None}

        shrunk_rows = list(probe.calc_box_widths())
        shrunk_widths = [row[3] for row in shrunk_rows]

        assert len(shrunk_rows) == 3
        assert sum(shrunk_widths) < 111
        assert any(width < 90 for width in shrunk_widths)
        assert any(row[1] is not None for row in shrunk_rows)
