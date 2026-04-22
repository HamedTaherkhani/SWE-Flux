from __future__ import annotations

from pathlib import Path

import pytest

from libqtile.scripts import check as check_mod


class _FakeProc:
    def __init__(self, stdout_text="", stderr_text="", returncode=0):
        self._stdout_text = stdout_text
        self._stderr_text = stderr_text
        self.returncode = returncode

    def communicate(self):
        return self._stdout_text, self._stderr_text

    def wait(self):
        return self.returncode


class _PopenFactory:
    def __init__(self, stdout_text, stderr_text, second_returncode):
        self.stdout_text = stdout_text
        self.stderr_text = stderr_text
        self.second_returncode = second_returncode
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return _FakeProc(stdout_text=self.stdout_text, stderr_text=self.stderr_text, returncode=0)
        if self.calls == 2:
            return _FakeProc(stdout_text="", stderr_text="", returncode=self.second_returncode)
        raise AssertionError("Unexpected extra subprocess.Popen call")


def _build_case(case_id: int):
    candidate_count = 3 + ((case_id * 11 + 5) % 8)
    candidates = [f"var_{case_id}_{i}" for i in range(candidate_count)]

    missing = []
    noise = []
    for idx, name in enumerate(candidates):
        selector = ((case_id + 2) * (idx + 3) + case_id * idx + 17) % 6
        if selector in (0, 1, 4):
            missing.append(name)
        else:
            noise.append(name)

    out_lines = [f"{name} is not present at runtime" for name in missing[::2]]
    err_lines = [f"{name} is not present at runtime" for name in missing[1::2]]
    out_lines.extend(f"note_{name} ignored-message" for name in noise)

    stdout_text = "\n".join(out_lines)
    stderr_text = "\n".join(err_lines)

    second_returncode = 0 if (case_id % 5 not in (1, 4)) else 1
    return stdout_text, stderr_text, len(missing), second_returncode


class TestScriptsCheckDirectTypeCheckConfigVarsMissingValuesRangeSuiteQA:
    @pytest.mark.parametrize("case_id", list(range(15)))
    def test_scripts_check_direct_type_check_config_vars_missing_values_range_case(
        self, case_id, tmp_path, monkeypatch
    ):
        stdout_text, stderr_text, expected_missing_count, second_returncode = _build_case(case_id)

        proc_factory = _PopenFactory(stdout_text, stderr_text, second_returncode)
        monkeypatch.setattr(check_mod.subprocess, "Popen", proc_factory)

        tempdir = tmp_path / f"case_{case_id}"
        tempdir.mkdir()

        config_name = f"cfg_case_{case_id}"

        if second_returncode == 0:
            check_mod.type_check_config_vars(str(tempdir), config_name)
        else:
            with pytest.raises(check_mod.CheckError):
                check_mod.type_check_config_vars(str(tempdir), config_name)

        whitelist = Path(tempdir) / "stubtest_whitelist"
        assert whitelist.exists()
        whitelist_lines = [line for line in whitelist.read_text(encoding="utf-8").splitlines() if line]

        assert len(whitelist_lines) == expected_missing_count
        assert proc_factory.calls == 2
