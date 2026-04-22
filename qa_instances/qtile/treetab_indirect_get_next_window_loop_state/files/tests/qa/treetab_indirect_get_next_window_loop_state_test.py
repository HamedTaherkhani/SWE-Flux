from types import SimpleNamespace

from libqtile.layout.tree import TreeTab


class DummyTreeWin:
    def __init__(self, name: str):
        self.name = name
        self.urgent = False

    def __repr__(self) -> str:
        return f"DummyTreeWin({self.name})"


class TestTreeTabIndirectGetNextWindowLoopStateQA:
    def test_treetab_indirect_get_next_window_loop_state_case(self):
        focus_events: list[tuple[str, bool]] = []

        layout = TreeTab(sections=["Main"])
        layout._group = SimpleNamespace(
            focus=lambda win, warp: focus_events.append((win.name, warp))
        )

        windows = {ch: DummyTreeWin(ch) for ch in "ABCDEFGHIJ"}
        for ch in "ABCDEFGHIJ":
            layout.add_client(windows[ch])

        # Build a non-trivial tree shape through command chaining.
        operations = [
            ("B", "move_right"),
            ("I", "move_right"),
            ("H", "move_right"),
            ("J", "move_right"),
            ("C", "move_down"),
            ("B", "move_up"),
            ("F", "move_down"),
            ("C", "move_left"),
        ]

        for win_name, command in operations:
            layout.focus(windows[win_name])
            getattr(layout, command)()

        # Indirect chain: TreeTab.next() -> TreeNode.get_next_window().
        layout.focus(windows["J"])
        layout.next()

        assert layout._focused is windows["F"]
        assert focus_events[-1] == ("F", False)
