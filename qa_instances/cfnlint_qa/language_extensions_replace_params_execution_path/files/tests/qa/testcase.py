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

from cfnlint.template.transforms._language_extensions import (
    _Transform,
)

_INPUT_S = "stk-${Stage}-${Cfg}-${Env}-${Owner}-&{Stage}-tail"
_INPUT_PARAMS = {
    "Stage": "prod-1",
    "Cfg": {"replicas": 3, "name": "alpha"},
    "Env": "dev",
    "Owner": {"team": "platform", "lead": "alice"},
}

class TestLanguageExtensionsReplaceParamsExecutionPathQA:
    def test_language_extensions_replace_params_execution_path_case(self):
        t = _Transform()
        only_string, new_s = t._replace_string_params(_INPUT_S, _INPUT_PARAMS)
        assert only_string is True
        assert new_s.startswith("stk-prod-1-")
        assert new_s.endswith("-prod1-tail")
        assert "${" not in new_s and "&{" not in new_s
