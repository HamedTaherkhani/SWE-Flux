from libqtile.core.state import QtileState


class _DummyGroup:
    def __init__(self, name: str):
        self.name = name
        self.layout = "init"
        self.label = ""

    def __repr__(self) -> str:
        return f"_DummyGroup({self.name})"


class _DummyScreen:
    def __init__(self, name: str):
        self.name = name
        self.group = None

    def set_group(self, group):
        self.group = group


class _DummyQtile:
    def __init__(self):
        self.groups_map = {"g1": _DummyGroup("g1")}
        self.groups = list(self.groups_map.values())
        self.screens = [_DummyScreen("s0"), _DummyScreen("s1")]
        self.windows_map = {}
        self.current_group = self.groups_map["g1"]
        self.add_group_calls = []
        self.focus_calls = []

    def add_group(self, group: str, layout: str, label: str | None = None):
        self.add_group_calls.append((group, layout, label))
        new_group = _DummyGroup(group)
        new_group.layout = layout
        new_group.label = label or ""
        self.groups_map[group] = new_group
        self.groups.append(new_group)

    def focus_screen(self, screen_index: int):
        self.focus_calls.append(screen_index)


class TestCoreStateDirectApplyCaughtExceptionKindsQA:
    def test_core_state_direct_apply_caught_exception_kinds_case(self):
        qtile = _DummyQtile()

        state = QtileState.__new__(QtileState)
        state.groups = [
            ("g1", "max", "primary"),
            ("missing_new", "columns", "created-by-except"),
        ]
        state.screens = {
            0: "g1",
            1: "missing_group",
            4: "g1",
        }
        state.current_screen = 0
        state.scratchpads = {}
        state.orphans = []
        state.restart = True

        state.apply(qtile)

        assert qtile.groups_map["g1"].layout == "max"
        assert qtile.groups_map["g1"].label == "primary"
        assert qtile.add_group_calls == [("missing_new", "columns", "created-by-except")]
        assert qtile.screens[0].group.name == "g1"
        assert qtile.screens[1].group is None
        assert qtile.focus_calls == [0]
