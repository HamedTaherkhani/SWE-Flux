from libqtile.layout.stack import Stack


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


class TestLayoutStackDirectConfigureExecutionPathLinesQA:
    def test_layout_stack_direct_configure_execution_path_lines_case(self):
        layout = Stack(
            num_stacks=3,
            border_focus="#2455aa",
            border_normal="#555555",
            border_focus_stack="#33aa77",
            border_normal_stack="#aa7733",
            border_width=4,
            margin=[2, 5, 3, 7],
            autosplit=False,
        )

        w1 = DummyWin("w1", has_focus=False)
        w2 = DummyWin("w2", has_focus=False)
        w3 = DummyWin("w3", has_focus=True)
        w4 = DummyWin("w4", has_focus=False)
        w5 = DummyWin("w5", has_focus=False)
        w6 = DummyWin("w6", has_focus=True)

        # Build explicit stack state to drive non-trivial branch flow.
        layout.stacks[0].clients = [w1, w2]
        layout.stacks[0].current_index = 1
        layout.stacks[0].split = False

        layout.stacks[1].clients = [w3]
        layout.stacks[1].current_index = 0
        layout.stacks[1].split = False

        layout.stacks[2].clients = [w4, w5, w6]
        layout.stacks[2].current_index = 2
        layout.stacks[2].split = True

        outsider = DummyWin("outsider", has_focus=False)

        # Warm-up call takes the not-found branch (hide + return).
        layout.configure(outsider, DummyRect(11, 19, 1003, 611))

        # Target call takes for-loop match + non-focus border path + split placement path.
        layout.configure(w5, DummyRect(19, 31, 1193, 703))

        assert outsider.hide_calls == 1
        assert outsider.unhide_calls == 0

        assert w5.hide_calls == 0
        assert w5.unhide_calls == 1
        assert len(w5.place_calls) == 1
        args, kwargs = w5.place_calls[0]
        assert args == (813, 265, 389, 226, 4, "#555555")
        assert kwargs == {"margin": [2, 5, 3, 7]}
