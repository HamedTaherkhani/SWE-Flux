from types import SimpleNamespace

from libqtile.layout.columns import Columns


class DummyWin:
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"DummyWin({self.name})"


class TestColumnsIndirectAddClientInputStateQA:
    def test_columns_indirect_add_client_input_state_case(self):
        layout = Columns(
            num_columns=3,
            insert_position=1,
            grow_amount=13,
            split=True,
            initial_ratio=1.7,
        )
        layout._group = SimpleNamespace(
            layout_all=lambda: None,
            focus=lambda *_args, **_kwargs: None,
        )

        windows = [DummyWin(f"w{i}") for i in range(1, 9)]
        for win in windows:
            layout.add_client(win)

        # Non-trivial state mutations before the final indirect call chain.
        layout.current = 2
        layout.cc.current_index = 1
        layout.grow_up()
        layout.grow_up()
        layout.grow_down()
        layout.shuffle_up()
        layout.grow_down()

        # Indirect target chain: shuffle_right -> add_column -> _Column.add_client.
        layout.shuffle_right()

        assert len(layout.columns) == 4
        assert [w.name for w in layout.columns[-1].clients] == ["w4"]
