from __future__ import annotations

import argparse
import json
from pathlib import Path


QUESTION = (
    "Use `tests/qa/base_bare_add_style_recursive_loop_state_test.py`, class "
    "`TestBaseBareAddStyleRecursiveLoopStateQA`, method "
    "`test_base_bare_add_style_recursive_loop_state_case`. The test directly calls "
    "`Bare._add_style_recursive(style, theme=None)` at "
    "`tests/qa/base_bare_add_style_recursive_loop_state_test.py:45` on a `Bare` "
    "component whose `contents` Var is assigned at "
    "`tests/qa/base_bare_add_style_recursive_loop_state_test.py:31` and carries "
    "three embedded components in its `VarData` at lines 34-36. The `style` input "
    "dictionary is assigned at `tests/qa/base_bare_add_style_recursive_loop_state_test.py:39-43`; "
    "the post-call `embedded_components` variable is assigned at line 47 and the "
    "summarizing `result` dictionary is assigned at lines 48-62. The target "
    "method is `reflex.components.base.bare.Bare._add_style_recursive`, defined at "
    "`reflex/components/base/bare.py:177`. In that method, local variable "
    "`new_self` is assigned after the `super()._add_style_recursive(...)` call at "
    "`reflex/components/base/bare.py:189`, local variable `are_components_touched` "
    "is initialized at line 191, the loop over `_components_from_var(self.contents)` "
    "runs at lines 193-197, the conditional `if are_components_touched` is evaluated "
    "at line 199, and the method returns at line 202. What is the exact state of "
    "`are_components_touched` and the embedded component styles after that loop and "
    "conditional complete? Return exactly the code variable or attribute expressions "
    "shown as keys in the template."
)


TEMPLATE_ANSWER = {
    "are_components_touched": "bool",
    "new_self is self": "bool",
    "new_self.style": {"str": "str"},
    "self.contents._get_all_var_data().components": [
        {"__class__": "str", "id": "str", "style": {"str": "str"}}
    ],
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
        "question_kind": "program_state_prediction",
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
