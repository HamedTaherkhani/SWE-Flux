from libqtile.layout.ratiotile import RatioTile


class DummyRatioWin:
    def __init__(self, name: str):
        self.name = name
        self.has_focus = False

    def __repr__(self) -> str:
        return f"DummyRatioWin({self.name})"

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


class TestRatioTileIndirectGetSizesLoopVarStateQA:
    def test_ratiotile_indirect_get_sizes_loop_var_state_case(self):
        layout = RatioTile(ratio=0.63, fancy=False)

        windows = [DummyRatioWin(f"w{i}") for i in range(1, 12)]
        for win in windows:
            layout.add_client(win)

        windows[3].has_focus = True
        screen_rect = DummyRect(17, 29, 997, 743)

        # Indirect chain: RatioTile.configure -> GridInfo.get_sizes(...)
        layout.configure(windows[3], screen_rect)

        assert len(layout.layout_info) == 11
        assert layout.layout_info[-1] == (614, 276, 199, 496)
