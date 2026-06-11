from __future__ import annotations

import argparse
import json
from pathlib import Path


QUESTION = (
    "Use `tests/qa/vars_function_partial_call_input_state_test.py`, class "
    "`TestVarsFunctionPartialCallInputStateQA`, method "
    "`test_vars_function_partial_call_input_state_case`. The test constructs "
    "local variables `handler` and `count` at "
    "`tests/qa/vars_function_partial_call_input_state_test.py:50-51`, then "
    "indirectly reaches the target by calling `handler.partial(\"alpha\", count)` "
    "at line 81. The outer method under test is "
    "`reflex.vars.function.FunctionVar.partial`, defined at "
    "`reflex/vars/function.py:112`; after the non-empty `args` branch at line 121, "
    "it calls `VarOperationCall.create(self, *args, Var(_js_expr=\"...args\"))` "
    "at `reflex/vars/function.py:123-126`. The specific inner method whose input "
    "variables are being asked about is "
    "`reflex.vars.function.VarOperationCall.create`, defined at "
    "`reflex/vars/function.py:268`. What are the exact values of input variables "
    "`func`, `args`, `_var_type`, and `_var_data` at the moment this inner method "
    "is called? For Var-like objects, report the object fields shown in the "
    "template, such as `_js_expr`, `_var_type`, `_var_data`, and `_original._js_expr`; "
    "do not answer with trace `repr(...)` strings."
)


TEMPLATE_ANSWER = {
    "func": {
        "__class__": "str",
        "_js_expr": "str",
        "_var_type": "str",
        "_var_data": "null | str",
    },
    "args": [
        "literal value or Var-like object summary with __class__, _js_expr, _var_type, _var_data, optional _original fields"
    ],
    "_var_type": "str",
    "_var_data": "null | str",
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
        "question_kind": "S3_ProgramState",
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
