import libqtile.core.manager as manager_mod
from libqtile.core.manager import Qtile


class DummyCommand:
    def __init__(self, name: str, should_run: bool = True, args=(), kwargs=None):
        self.selectors = ["root"]
        self.name = name
        self.args = args
        self.kwargs = kwargs or {}
        self.should_run = should_run
        self.check_calls = 0

    def check(self, _qtile):
        self.check_calls += 1
        return self.should_run


class DummyClick:
    def __init__(self, modmask: int, commands: list[DummyCommand]):
        self.modmask = modmask
        self.commands = commands


class DummyDrag:
    def __init__(
        self,
        modmask: int,
        commands: list[DummyCommand],
        start: DummyCommand | None,
        warp_pointer: bool,
    ):
        self.modmask = modmask
        self.commands = commands
        self.start = start
        self.warp_pointer = warp_pointer


class DummyWindow:
    def __init__(self):
        self.fullscreen = False

    def get_size(self):
        return (300, 200)

    def get_position(self):
        return (40, 60)


class DummyCore:
    def __init__(self):
        self.warp_calls = []
        self.grab_pointer_calls = 0

    def warp_pointer(self, x, y):
        self.warp_calls.append((x, y))

    def grab_pointer(self):
        self.grab_pointer_calls += 1


class DummyConfig:
    def __init__(self):
        self.follow_mouse_focus = "click_or_drag_only"


class DummyServer:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def call(self, payload):
        self.calls.append(payload)
        if self.responses:
            return self.responses.pop(0)
        return (0, "default")


class DummyQtileProcessButtonProbe:
    process_button_click = Qtile.process_button_click

    def __init__(self, responses):
        self._mouse_map = {1: []}
        self.current_window = DummyWindow()
        self._drag = None
        self.config = DummyConfig()
        self.server = DummyServer(responses)
        self.core = DummyCore()
        self.focus_hovered_calls = 0

    def _focus_hovered_window(self):
        self.focus_hovered_calls += 1


class TestCoreManagerDirectProcessButtonClickDefUsePairsQA:
    def test_core_manager_direct_process_button_click_def_use_pairs_case(self):
        interface = manager_mod.interface
        responses = [
            (0, "click-ok"),
            (interface.ERROR, "click-error"),
            (interface.EXCEPTION, "drag-start-error"),
            (0, (13, 17)),
        ]
        probe = DummyQtileProcessButtonProbe(responses)

        click_a = DummyCommand("click_a", True, args=(1,))
        click_b = DummyCommand("click_b", False, args=(2,))
        click_c = DummyCommand("click_c", True, args=(3,))

        start_bad = DummyCommand("start_bad", True, args=(10,))
        start_ok = DummyCommand("start_ok", True, args=(11,))
        drag_cmd_a = DummyCommand("drag_a", True, args=(21,))
        drag_cmd_b = DummyCommand("drag_b", True, args=(22,))

        wrong_click = DummyClick(modmask=3, commands=[click_a])
        good_click = DummyClick(modmask=7, commands=[click_a, click_b, click_c])
        bad_drag = DummyDrag(modmask=7, commands=[drag_cmd_a], start=start_bad, warp_pointer=True)
        good_drag = DummyDrag(
            modmask=7,
            commands=[drag_cmd_a, drag_cmd_b],
            start=start_ok,
            warp_pointer=True,
        )

        probe._mouse_map[1] = [wrong_click, good_click, bad_drag, good_drag]

        orig_click = manager_mod.Click
        orig_drag = manager_mod.Drag
        manager_mod.Click = DummyClick
        manager_mod.Drag = DummyDrag
        try:
            handled = probe.process_button_click(button_code=1, modmask=7, x=15, y=25)
        finally:
            manager_mod.Click = orig_click
            manager_mod.Drag = orig_drag

        assert handled is True
        assert probe.focus_hovered_calls == 3
        assert probe.core.grab_pointer_calls == 1
        assert probe.core.warp_calls == [(340, 260)]
        assert probe._drag == (340, 260, 13, 17, good_drag.commands)

        assert len(probe.server.calls) == 4
        assert click_a.check_calls == 1
        assert click_b.check_calls == 1
        assert click_c.check_calls == 1
