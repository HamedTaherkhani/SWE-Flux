from libqtile.layout.columns import Columns


class DummyWin:
    def __init__(self, name: str, has_focus: bool = False):
        self.name = name
        self.has_focus = has_focus
        self.place_calls = []
        self.hide_calls = 0
        self.unhide_calls = 0

    def place(self, *args, **kwargs):
        self.place_calls.append((args, kwargs))

    def hide(self):
        self.hide_calls += 1

    def unhide(self):
        self.unhide_calls += 1


class DummyRect:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class TestLayoutColumnsDirectConfigureExecutionPathLinesQA:
    def test_layout_columns_direct_configure_execution_path_lines_case(self):
        layout = Columns(
            num_columns=3,
            split=False,
            fair=False,
            initial_ratio=1.6,
            border_focus="#55aaee",
            border_normal="#101010",
            border_focus_stack="#2266cc",
            border_normal_stack="#774422",
            border_width=5,
            margin=[1, 2, 3, 4],
            margin_on_single=[7, 7, 7, 7],
            border_on_single=True,
            single_border_width=9,
        )

        col0 = layout.columns[0]
        col1 = layout.add_column(prepend=False)
        col2 = layout.add_column(prepend=False)

        # Keep deterministic width proportions for easier validation.
        col0.width = 100
        col1.width = 100
        col2.width = 100

        w1 = DummyWin("w1", has_focus=False)
        w2 = DummyWin("w2", has_focus=False)
        w3 = DummyWin("w3", has_focus=True)
        w4 = DummyWin("w4", has_focus=False)
        w5 = DummyWin("w5", has_focus=False)
        w6 = DummyWin("w6", has_focus=True)

        col0.add_client(w1)

        col1.add_client(w2)
        col1.add_client(w3)
        col1.split = False
        col1.current_index = col1.clients.index(w3)

        col2.add_client(w4)
        col2.add_client(w5)
        col2.add_client(w6)
        col2.split = True
        col2.heights[w4] = 45
        col2.heights[w5] = 35
        col2.heights[w6] = 20

        outsider = DummyWin("outsider", has_focus=False)

        screen = DummyRect(17, 23, 1361, 777)

        # 1) Not-found branch.
        layout.configure(outsider, screen)
        # 2) Non-split current-window branch.
        layout.configure(w3, screen)
        # 3) Split branch with inner loop over column members.
        layout.configure(w5, screen)

        assert outsider.hide_calls == 1
        assert outsider.unhide_calls == 0

        assert w3.hide_calls == 0
        assert w3.unhide_calls == 1
        assert len(w3.place_calls) == 1
        args3, kwargs3 = w3.place_calls[0]
        assert args3 == (471, 23, 444, 767, 5, "#2266cc")
        assert kwargs3 == {"margin": [1, 2, 3, 4]}

        assert w5.hide_calls == 0
        assert w5.unhide_calls == 1
        assert len(w5.place_calls) == 1
        args5, kwargs5 = w5.place_calls[0]
        assert args5 == (924, 75, 444, 81, 5, "#101010")
        assert kwargs5 == {"margin": [1, 2, 3, 4]}
