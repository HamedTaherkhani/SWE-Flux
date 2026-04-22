import os

import libqtile.core.manager as manager_mod
from libqtile.core.manager import Qtile


class DummyLayout:
    def __init__(self, name: str):
        self.name = name


class DummyGroup:
    def __init__(self, name: str, layout_name: str, label: str):
        self.name = name
        self.layout = DummyLayout(layout_name)
        self.label = label


class DummyScreen:
    def __init__(self, name: str, group: DummyGroup):
        self.name = name
        self.group = group


class DummyConfig:
    def __init__(self):
        self.load_calls = 0

    def load(self):
        self.load_calls += 1


class DummyStoppedEvent:
    def __init__(self):
        self.set_calls = 0

    def set(self):
        self.set_calls += 1


class DummyQtileRestartProbe:
    restart = Qtile.restart
    dump_state = Qtile.dump_state
    _stop = Qtile._stop

    def __init__(self):
        self.core = type("Core", (), {"supports_restarting": True, "name": "x11"})()
        self.config = DummyConfig()

        g1 = DummyGroup("g1", "max", "A")
        g2 = DummyGroup("g2", "columns", "B")
        g3 = DummyGroup("g3", "stack", "C")
        self.groups = [g1, g2, g3]

        s0 = DummyScreen("s0", g1)
        s1 = DummyScreen("s1", g2)
        self.screens = [s0, s1]
        self.current_screen = s1

        self._stopped_event = DummyStoppedEvent()


class TestCoreManagerRestartStateInitExecutionPathLinesQA:
    def test_core_manager_restart_state_init_execution_path_lines_case(self):
        probe = DummyQtileRestartProbe()

        old_behavior = manager_mod.lifecycle.behavior
        old_state_file = manager_mod.lifecycle.state_file

        try:
            probe.restart()

            assert probe.config.load_calls == 1
            assert probe._stopped_event.set_calls == 1

            state_file = manager_mod.lifecycle.state_file
            assert isinstance(state_file, str)
            assert os.path.exists(state_file)
            assert os.path.getsize(state_file) > 0
        finally:
            state_file = manager_mod.lifecycle.state_file
            if isinstance(state_file, str) and os.path.exists(state_file):
                os.remove(state_file)
            manager_mod.lifecycle.behavior = old_behavior
            manager_mod.lifecycle.state_file = old_state_file
