from __future__ import annotations

import argparse
import json
from pathlib import Path


QUESTION = (
    "Use `tests/qa/vars_sequence_foreach_args_function_input_state_test.py`, class "
    "`TestVarsSequenceForeachArgsFunctionInputStateQA`, method "
    "`test_vars_sequence_foreach_args_function_input_state_case`. The test "
    "constructs local variable `rows` at "
    "`tests/qa/vars_sequence_foreach_args_function_input_state_test.py:51-54`, "
    "patches `get_unique_variable_name` to return `qa_row` at line 86, and then "
    "indirectly reaches the target by calling `rows.foreach(lambda item: "
    "item[\"score\"] + item[\"bonus\"] * 2)` at line 93. The outer method under "
    "test is `reflex.vars.sequence.ArrayVar.foreach`, defined at "
    "`reflex/vars/sequence.py:440`; in the one-argument branch it computes "
    "`first_arg_type`, `arg_name`, and `first_arg` at lines 467-478, then calls "
    "`ArgsFunctionOperation.create((arg_name,), Var.create(fn(first_arg)))` at "
    "`reflex/vars/sequence.py:480-483`. The specific inner method whose input "
    "variables are being asked about is "
    "`reflex.vars.function.ArgsFunctionOperation.create`, defined at "
    "`reflex/vars/function.py:383`. What are the exact states of input variables "
    "`args_names`, `return_expr`, `rest`, `explicit_return`, `_var_type`, and "
    "`_var_data` at the moment this inner method is called? For Var-like objects, "
    "report the object fields shown in the template, such as `_js_expr`, "
    "`_var_type`, `_var_data`, and `_original._js_expr`; do not answer with trace "
    "`repr(...)` strings."
)


TEMPLATE_ANSWER = {
    "args_names": ["str"],
    "return_expr": {
        "__class__": "str",
        "_js_expr": "str",
        "_var_type": "str",
        "_var_data": "null | str",
        "_original._js_expr": "str",
        "_original.__class__": "str",
    },
    "rest": "null | str",
    "explicit_return": "bool",
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
        "question_kind": "C4_ProgramState",
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
