from __future__ import annotations

import sys
from pathlib import Path

def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "src" / "cfnlint").is_dir():
            return p
    raise RuntimeError("Could not locate cfnlint source tree (expected .../src/cfnlint).")

_REPO_ROOT = _find_repo_root()
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from cfnlint.template.transforms._language_extensions import _Transform

def _t() -> _Transform:
    return _Transform()

def _params(n: int) -> dict[str, str]:
    return {f"K{i}": f"v{i}" for i in range(n)}

def _params_mixed(n: int) -> dict[str, object]:
    out: dict[str, object] = {}
    for i in range(n):
        if i % 2 == 0:
            out[f"K{i}"] = f"plain{i}"
        else:
            out[f"K{i}"] = {"nested": f"obj{i}"}
    return out

_PAT = "stk-${K0}-tail"
_PAT_AMP = "stk-&{K0}-tail"
_PAT_NONE = "plain string no pattern"

class TestReplaceStringParamsLoopTotalIterationsQA:

    def test_replace_string_params_loop_total_iterations_case_01(self):
        t = _t()
        t._replace_string_params(_PAT, _params(12))

    def test_replace_string_params_loop_total_iterations_case_02(self):
        t = _t()
        t._replace_string_params(_PAT_AMP, _params(12))

    def test_replace_string_params_loop_total_iterations_case_03(self):
        t = _t()
        t._replace_string_params(_PAT, _params(6))
        t._replace_string_params(_PAT, _params(6))

    def test_replace_string_params_loop_total_iterations_case_04(self):
        t = _t()
        for _ in range(3):
            t._replace_string_params(_PAT, _params(4))

    def test_replace_string_params_loop_total_iterations_case_05(self):
        t = _t()
        for _ in range(4):
            t._replace_string_params(_PAT, _params(3))

    def test_replace_string_params_loop_total_iterations_case_06(self):
        t = _t()
        for _ in range(6):
            t._replace_string_params(_PAT, _params(2))

    def test_replace_string_params_loop_total_iterations_case_07(self):
        t = _t()
        for _ in range(12):
            t._replace_string_params(_PAT, _params(1))

    def test_replace_string_params_loop_total_iterations_case_08(self):
        t = _t()
        t._replace_string_params(_PAT, _params(12))
        t._replace_string_params(_PAT_NONE, _params(50))
        t._replace_string_params(_PAT_NONE, _params(7))
        t._replace_string_params(_PAT_NONE, _params(99))

    def test_replace_string_params_loop_total_iterations_case_09(self):
        t = _t()
        t._replace_string_params(_PAT, _params(6))
        t._replace_string_params(_PAT_NONE, _params(20))
        t._replace_string_params(_PAT, _params(6))
        t._replace_string_params(_PAT_NONE, _params(8))
        t._replace_string_params(_PAT_NONE, _params(15))

    def test_replace_string_params_loop_total_iterations_case_10(self):
        t = _t()
        t._replace_string_params(_PAT, _params(8))
        t._replace_string_params(_PAT, _params(4))

    def test_replace_string_params_loop_total_iterations_case_11(self):
        t = _t()
        t._replace_string_params(_PAT, _params(5))
        t._replace_string_params(_PAT, _params(7))

    def test_replace_string_params_loop_total_iterations_case_12(self):
        t = _t()
        t._replace_string_params(_PAT, _params(11))
        t._replace_string_params(_PAT, _params(1))

    def test_replace_string_params_loop_total_iterations_case_13(self):
        t = _t()
        t._replace_string_params(_PAT, _params(6))
        t._replace_string_params(_PAT, _params(6))
        t._replace_string_params(_PAT, {})

    def test_replace_string_params_loop_total_iterations_case_14(self):
        t = _t()
        t._replace_string_params(_PAT, _params(9))
        t._replace_string_params(_PAT, _params(3))
        t._replace_string_params(_PAT, {})
        t._replace_string_params(_PAT_NONE, _params(99))

    def test_replace_string_params_loop_total_iterations_case_15(self):
        t = _t()
        t._replace_string_params(_PAT, _params_mixed(6))
        t._replace_string_params(_PAT, _params(6))
