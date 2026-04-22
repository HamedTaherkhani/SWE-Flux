from types import SimpleNamespace

from libqtile.layout.xmonad import MonadTall


class TestXMonadTallIndirectShrinkInputStateQA:
    def test_xmonadtall_indirect_shrink_input_state_case(self):
        layout = MonadTall(change_size=37, min_secondary_size=77)
        layout._group = SimpleNamespace(layout_all=lambda: None)

        # Six clients means one main + five secondary slots in Monadtall logic.
        layout.clients.clients = [object() for _ in range(6)]

        # Focus the 4th client (index 3): this is a middle secondary pane.
        layout.clients.current_index = 3

        # Screen height controls relative<->absolute size conversion in _shrink.
        layout.screen_rect = SimpleNamespace(height=913)

        # Non-uniform secondary sizes to make shrink distribution path non-trivial.
        layout.relative_sizes = [0.19, 0.27, 0.21, 0.33]

        layout.grow()

        assert len(layout.relative_sizes) == 4
        assert all(size > 0 for size in layout.relative_sizes)
        assert abs(sum(layout.relative_sizes) - 1.0) < 1e-9
