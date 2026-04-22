from __future__ import annotations

import pytest

from libqtile.core import manager as manager_mod
from libqtile.core.manager import Qtile


class DummyCall:
    def __init__(self, name, args=None, kwargs=None):
        self.name = name
        self.args = list(args or [])
        self.kwargs = dict(kwargs or {})


class FakeKey:
    def __init__(self, key, modifiers=None, commands=None, desc=""):
        self.key = key
        self.modifiers = list(modifiers or [])
        self.commands = list(commands or [])
        self.desc = desc


class FakeKeyChord:
    def __init__(self, key, modifiers=None, submappings=None, name=None):
        self.key = key
        self.modifiers = list(modifiers or [])
        self.submappings = list(submappings or [])
        self.name = name


class DummyConfig:
    def __init__(self, keys):
        self.keys = list(keys)


class DummyDisplayKbProbe:
    display_kb = Qtile.display_kb

    def __init__(self, keys):
        self.config = DummyConfig(keys)


def make_simple_key(name, command_name, desc, modifiers=None):
    return FakeKey(
        key=name,
        modifiers=modifiers or [],
        commands=[DummyCall(command_name)],
        desc=desc,
    )


class UnknownMapping:
    def __init__(self):
        self.modifiers = []
        self.key = "?"


CASES = [
    {
        "name": "root_simple_key",
        "keys_factory": lambda: [make_simple_key("a", "focus_next", "Focus next", ["mod4"])],
        "must_include": ["focus_next()", "Focus next", "<root>"],
        "must_exclude": [],
        "raises_typeerror": False,
    },
    {
        "name": "integer_keysym_hex_formatting",
        "keys_factory": lambda: [make_simple_key(255, "set_mode", "Set mode", ["control", "mod1"])],
        "must_include": ["0xff", "set_mode()"],
        "must_exclude": [],
        "raises_typeerror": False,
    },
    {
        "name": "callable_and_kwargs_rendering",
        "keys_factory": lambda: [
            FakeKey(
                key="x",
                modifiers=["mod4", "shift"],
                commands=[DummyCall("apply", args=[abs, "txt"], kwargs={"step": 3, "flag": True})],
                desc="Apply advanced",
            )
        ],
        "must_include": ["apply(abs, 'txt', step = 3, flag = True)", "Apply advanced"],
        "must_exclude": [],
        "raises_typeerror": False,
    },
    {
        "name": "empty_commands_are_ignored",
        "keys_factory": lambda: [
            FakeKey(key="z", modifiers=["mod4"], commands=[], desc="Should not be rendered"),
            make_simple_key("b", "launch", "Launch", ["mod4"]),
        ],
        "must_include": ["launch()", "Launch"],
        "must_exclude": ["Should not be rendered"],
        "raises_typeerror": False,
    },
    {
        "name": "named_chord_root_mode",
        "keys_factory": lambda: [
            FakeKeyChord(
                key="r",
                modifiers=["mod4"],
                name="resize",
                submappings=[make_simple_key("h", "grow_left", "Grow left", ["mod4"])],
            )
        ],
        "must_include": ["Enter resize mode", "grow_left()"],
        "must_exclude": [],
        "raises_typeerror": False,
    },
    {
        "name": "unnamed_chord_root_mode",
        "keys_factory": lambda: [
            FakeKeyChord(
                key="u",
                modifiers=["mod4"],
                name=None,
                submappings=[make_simple_key("j", "move_down", "Move down", ["mod4"])],
            )
        ],
        "must_include": [],
        "must_exclude": [],
        "raises_typeerror": True,
    },
    {
        "name": "nested_chord_underscore_mode_path",
        "keys_factory": lambda: [
            FakeKeyChord(
                key="m",
                modifiers=["mod4"],
                name="main",
                submappings=[
                    FakeKeyChord(
                        key="n",
                        modifiers=["mod4"],
                        name=None,
                        submappings=[make_simple_key("k", "jump", "Jump", ["shift"])],
                    )
                ],
            )
        ],
        "must_include": ["Enter main mode", "main>_", "jump()"],
        "must_exclude": [],
        "raises_typeerror": False,
    },
    {
        "name": "sorted_rows_across_modes",
        "keys_factory": lambda: [
            make_simple_key("z", "zzz", "Z item", ["mod4"]),
            make_simple_key("a", "aaa", "A item", ["mod4"]),
            FakeKeyChord(
                key="c",
                modifiers=["mod4"],
                name="cmds",
                submappings=[make_simple_key("b", "bbb", "B item", ["mod4"])],
            ),
        ],
        "must_include": ["aaa()", "bbb()", "zzz()", "Enter cmds mode"],
        "must_exclude": [],
        "raises_typeerror": False,
    },
    {
        "name": "deep_mixed_keysym_types",
        "keys_factory": lambda: [
            FakeKeyChord(
                key=4096,
                modifiers=[],
                name="deep",
                submappings=[
                    make_simple_key(16, "intkey", "int key", []),
                    make_simple_key("s", "strkey", "str key", ["mod1"]),
                ],
            )
        ],
        "must_include": ["0x1000", "0x10", "intkey()", "strkey()"],
        "must_exclude": [],
        "raises_typeerror": False,
    },
    {
        "name": "unexpected_mapping_type_raises",
        "keys_factory": lambda: [UnknownMapping()],
        "must_include": [],
        "must_exclude": [],
        "raises_typeerror": True,
    },
]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
class TestCoreManagerDirectDisplayKbLineCoverageSuiteQA:
    def test_core_manager_direct_display_kb_line_coverage_suite_case(self, case, monkeypatch):
        monkeypatch.setattr(manager_mod, "Key", FakeKey)
        monkeypatch.setattr(manager_mod, "KeyChord", FakeKeyChord)

        probe = DummyDisplayKbProbe(case["keys_factory"]())

        if case["raises_typeerror"]:
            with pytest.raises(TypeError):
                probe.display_kb()
            return

        output = probe.display_kb()
        assert "Mode" in output
        assert "KeySym" in output
        assert "Command" in output

        for token in case["must_include"]:
            assert token in output
        for token in case["must_exclude"]:
            assert token not in output

        if case["name"] == "sorted_rows_across_modes":
            assert output.index("aaa()") < output.index("zzz()")
