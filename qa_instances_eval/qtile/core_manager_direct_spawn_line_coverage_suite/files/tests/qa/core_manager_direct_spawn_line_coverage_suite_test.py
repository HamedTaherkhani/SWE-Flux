from __future__ import annotations

import shlex
import subprocess
import sys

import pytest

from libqtile.core import manager as manager_mod
from libqtile.core.manager import Qtile


class DummyQtileSpawnProbe:
    spawn = Qtile.spawn


CASES = [
    {"name": "str_basic_success", "cmd": "echo hello", "shell": False, "which": True, "custom_env": False, "spawn_error": False},
    {"name": "str_with_quotes", "cmd": "printf 'x y'", "shell": False, "which": True, "custom_env": False, "spawn_error": False},
    {"name": "str_shell_success", "cmd": "echo hi | cat", "shell": True, "which": True, "custom_env": False, "spawn_error": False},
    {"name": "list_basic_success", "cmd": ["python3", "-c", "print(1)"], "shell": False, "which": True, "custom_env": False, "spawn_error": False},
    {"name": "list_shell_success", "cmd": ["bash", "-lc", "echo ok"], "shell": True, "which": True, "custom_env": False, "spawn_error": False},
    {"name": "which_missing_str", "cmd": "missingcmd --flag", "shell": False, "which": False, "custom_env": False, "spawn_error": False},
    {"name": "which_missing_list", "cmd": ["missingbin", "arg1"], "shell": True, "which": False, "custom_env": False, "spawn_error": False},
    {"name": "spawn_oserror_str", "cmd": "ls -la", "shell": False, "which": True, "custom_env": False, "spawn_error": True},
    {"name": "spawn_oserror_list_shell", "cmd": ["zsh", "-lc", "echo z"], "shell": True, "which": True, "custom_env": False, "spawn_error": True},
    {"name": "custom_env_success", "cmd": "env", "shell": False, "which": True, "custom_env": True, "spawn_error": False},
    {"name": "custom_env_shell_success", "cmd": ["env"], "shell": True, "which": True, "custom_env": True, "spawn_error": False},
    {"name": "custom_env_spawn_error", "cmd": "echo final", "shell": False, "which": True, "custom_env": True, "spawn_error": True},
]


def expected_args(cmd, shell):
    if isinstance(cmd, str):
        args = shlex.split(cmd)
        cmd_string = cmd
    else:
        args = list(cmd)
        cmd_string = subprocess.list2cmdline(args)

    to_lookup = args[0]
    if shell:
        return to_lookup, ["/bin/sh", "-c", cmd_string]
    return to_lookup, args


@pytest.mark.parametrize("case_index,case", list(enumerate(CASES)), ids=[c["name"] for c in CASES])
class TestCoreManagerDirectSpawnLineCoverageSuiteQA:
    def test_core_manager_direct_spawn_line_coverage_suite_case(self, case_index, case, monkeypatch):
        which_calls = []
        spawn_calls = []

        def fake_which(binary):
            which_calls.append(binary)
            if case["which"]:
                return f"/usr/bin/{binary}"
            return None

        def fake_spawnp(file, args, env, file_actions=None):
            spawn_calls.append(
                {
                    "file": file,
                    "args": list(args),
                    "env": dict(env),
                    "file_actions": list(file_actions or []),
                }
            )
            if case["spawn_error"]:
                raise OSError("synthetic spawn failure")
            return 4200 + case_index

        monkeypatch.setattr(manager_mod.shutil, "which", fake_which)
        monkeypatch.setattr(manager_mod.os, "posix_spawnp", fake_spawnp)
        monkeypatch.setattr(manager_mod.os, "environ", {"PATH": "/usr/bin", "VIRTUAL_ENV": "/tmp/venv"})

        if case["custom_env"]:
            env_arg = {"PATH": "/bin", "CUSTOM": "1", "VIRTUAL_ENV": "keep-me"}
        else:
            env_arg = {}

        probe = DummyQtileSpawnProbe()
        result = probe.spawn(case["cmd"], shell=case["shell"], env=env_arg)

        lookup, args_expected = expected_args(case["cmd"], case["shell"])
        assert which_calls == [lookup]

        if not case["which"]:
            assert result == -1
            assert spawn_calls == []
            return

        assert len(spawn_calls) == 1
        spawn_call = spawn_calls[0]
        assert spawn_call["file"] == args_expected[0]
        assert spawn_call["args"] == args_expected
        assert len(spawn_call["file_actions"]) == 3 + (1 if sys.version_info[:2] >= (3, 13) else 0)

        if case["custom_env"]:
            assert spawn_call["env"] == env_arg
        else:
            assert spawn_call["env"].get("PATH") == "/usr/bin"
            assert "VIRTUAL_ENV" not in spawn_call["env"]

        if case["spawn_error"]:
            assert result == -1
        else:
            assert result == 4200 + case_index
