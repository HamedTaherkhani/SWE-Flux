from types import SimpleNamespace

from libqtile.layout.bsp import Bsp


class DummyBspWin:
    def __init__(self, name: str):
        self.name = name
        self.has_focus = False

    def __repr__(self) -> str:
        return f"DummyBspWin({self.name})"

    def place(self, *args, **kwargs):
        return None

    def unhide(self):
        return None

    def hide(self):
        return None


class DummyRect:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class TestBspIndirectCalcGeomInputStateQA:
    def test_bsp_indirect_calc_geom_input_state_case(self):
        layout = Bsp(ratio=1.37, grow_amount=13, fair=True, lower_right=True)
        layout._group = SimpleNamespace(layout_all=lambda: None, focus=lambda *_args, **_kwargs: None)

        windows = [DummyBspWin(f"w{i}") for i in range(1, 9)]
        for win in windows:
            layout.add_client(win)

        # Mutate tree structure and split ratios before the final configure call.
        layout.focus(windows[6])
        layout.toggle_split()
        layout.grow_up()
        layout.focus(windows[2])
        layout.toggle_split()
        layout.grow_down()
        layout.focus(windows[7])
        layout.toggle_split()
        layout.grow_left()
        layout.focus(windows[4])
        layout.grow_right()

        screen_rect = DummyRect(23, 41, 1531, 901)
        windows[0].has_focus = True

        # Indirect call chain: configure -> root.calc_geom -> recursive calc_geom calls.
        layout.configure(windows[0], screen_rect)

        assert layout.root.w == 1531
        assert layout.root.h == 901
