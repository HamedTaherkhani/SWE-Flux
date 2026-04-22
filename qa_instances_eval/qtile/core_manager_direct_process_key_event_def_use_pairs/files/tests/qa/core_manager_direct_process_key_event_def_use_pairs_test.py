import libqtile.core.manager as manager_mod
from libqtile.core.manager import Qtile


class DummyCommand:
    def __init__(self, name: str, should_run: bool, args=(), kwargs=None):
        self.selectors = ["root"]
        self.name = name
        self.args = args
        self.kwargs = kwargs or {}
        self.should_run = should_run
        self.check_calls = 0

    def check(self, _qtile):
        self.check_calls += 1
        return self.should_run


class DummyKey:
    def __init__(self, key: str, commands: list[DummyCommand], swallow: bool):
        self.key = key
        self.commands = commands
        self.swallow = swallow


class DummyChord:
    def __init__(self, mode: bool):
        self.mode = mode


class DummyServer:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def call(self, payload):
        self.calls.append(payload)
        if self.responses:
            return self.responses.pop(0)
        return (0, "default")


class DummyQtileProcessKeyProbe:
    process_key_event = Qtile.process_key_event

    def __init__(self, responses):
        self.keys_map = {}
        self.chord_stack = []
        self.server = DummyServer(responses)
        self.ungrab_chord_calls = 0
        self.grab_chord_calls = 0

    def grab_chord(self, _chord):
        self.grab_chord_calls += 1

    def ungrab_chord(self):
        self.ungrab_chord_calls += 1


class TestCoreManagerDirectProcessKeyEventDefUsePairsQA:
    def test_core_manager_direct_process_key_event_def_use_pairs_case(self):
        interface = manager_mod.interface
        responses = [
            (0, "ok-main"),
            (interface.ERROR, "main-error"),
            (interface.EXCEPTION, "escape-error"),
        ]
        probe = DummyQtileProcessKeyProbe(responses)

        cmd_main_a = DummyCommand("main_a", True, args=(1,))
        cmd_main_b = DummyCommand("main_b", False, args=(2,))
        cmd_main_c = DummyCommand("main_c", True, args=(3,))
        key_main = DummyKey("a", [cmd_main_a, cmd_main_b, cmd_main_c], swallow=True)

        cmd_noexec = DummyCommand("noexec", False, args=(4,))
        key_noexec = DummyKey("z", [cmd_noexec], swallow=True)

        cmd_escape = DummyCommand("escape", True, args=(5,))
        key_escape = DummyKey("Escape", [cmd_escape], swallow=True)

        probe.keys_map[(22, 2)] = key_main
        probe.keys_map[(33, 3)] = key_noexec
        probe.keys_map[(44, 4)] = key_escape

        r0 = probe.process_key_event(11, 1)

        probe.chord_stack = [DummyChord(mode=False)]
        r1 = probe.process_key_event(22, 2)

        probe.chord_stack = []
        r2 = probe.process_key_event(33, 3)

        probe.chord_stack = [DummyChord(mode=True)]
        r3 = probe.process_key_event(44, 4)

        assert r0 == (None, False)
        assert r1 == (key_main, True)
        assert r2 == (key_noexec, False)
        assert r3 == (key_escape, True)

        assert probe.ungrab_chord_calls == 2
        assert probe.grab_chord_calls == 0

        assert len(probe.server.calls) == 3
        assert cmd_main_a.check_calls == 1
        assert cmd_main_b.check_calls == 1
        assert cmd_main_c.check_calls == 1
        assert cmd_noexec.check_calls == 1
        assert cmd_escape.check_calls == 1
