from __future__ import annotations

import argparse
import json
from pathlib import Path


QUESTION = (
    "Use `tests/qa/base_bare_get_all_imports_dict_keys_test.py`, class "
    "`TestBaseBareGetAllImportsDictKeysQA`, method "
    "`test_base_bare_get_all_imports_dict_keys_case`. The test directly calls "
    "`bare._get_all_imports(collapse=False)` at "
    "`tests/qa/base_bare_get_all_imports_dict_keys_test.py:50` on a `Bare` "
    "component whose `merged_var_data` variable is assigned at "
    "`tests/qa/base_bare_get_all_imports_dict_keys_test.py:27-41` from a state "
    "var, custom imports, hooks, and two embedded components. The `bare` variable "
    "is assigned at lines 42-48, the post-call `imports` variable is assigned at "
    "line 50, local `var_data` is assigned at line 51, and the summarizing `result` "
    "dictionary is assigned at lines 52-66. "
    "The target method is "
    "`reflex.components.base.bare.Bare._get_all_imports`, defined at "
    "`reflex/components/base/bare.py:105`. Inside the target, dictionary variable "
    "`imports` is assigned from `super()._get_all_imports(...)` at "
    "`reflex/components/base/bare.py:114`; local variable `var_data` is assigned "
    "from `self.contents._get_all_var_data()` at line 116; the dictionary is then "
    "updated with `var_data.imports` at line 118 and returned at line 119. What "
    "dictionary keys does local variable `imports` hold at return, and what import "
    "tags are stored under each key? Return exactly the code variable or attribute "
    "expressions shown as keys in the template."
)


TEMPLATE_ANSWER = {
    "imports.keys()": ["str"],
    "imports.items()": {"str": ["str"]},
    "var_data.imports": {"str": ["str"]},
    "var_data.components": [{"__class__": "str"}],
}


def extract_result(pytest_log: Path) -> dict:
    for line in pytest_log.read_text(encoding="utf-8").splitlines():
        if "QA_RESULT_JSON=" in line:
            return json.loads(line.split("QA_RESULT_JSON=", 1)[1])
    raise RuntimeError(f"QA_RESULT_JSON marker not found in {pytest_log}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pytest-log", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    oracle = {
        "question_kind": "S4_ProgramState",
        "question": QUESTION,
        "template_answer": TEMPLATE_ANSWER,
        "oracle_answer": extract_result(Path(args.pytest_log)),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(oracle, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps(oracle, indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
