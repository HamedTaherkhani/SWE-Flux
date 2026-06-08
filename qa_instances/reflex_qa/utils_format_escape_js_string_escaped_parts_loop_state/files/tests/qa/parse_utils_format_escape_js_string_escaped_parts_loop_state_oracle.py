from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


QUESTION = (
    "Use `tests/qa/utils_format_escape_js_string_escaped_parts_loop_state_test.py`, "
    "class `TestUtilsFormatEscapeJsStringEscapedPartsLoopStateQA`, method "
    "`test_utils_format_escape_js_string_escaped_parts_loop_state_case`. The test "
    "directly calls `_escape_js_string(string)` at "
    "`tests/qa/utils_format_escape_js_string_escaped_parts_loop_state_test.py:13`. "
    "The target function is `reflex.utils.format._escape_js_string`, defined at "
    "`reflex/utils/format.py:241`. In that function, local variable `parts` is "
    "assigned by `re.split(...)` at `reflex/utils/format.py:271`, and the single "
    "target variable `escaped_parts` is assigned by the list comprehension at "
    "`reflex/utils/format.py:272`. That comprehension calls nested function "
    "`escape_outside_segments`, whose conditional at `reflex/utils/format.py:261` "
    "leaves `${...}` segments unchanged and whose `else` branch at lines 264-268 "
    "escapes backticks in outside segments. What is the exact state of the single "
    "target variable `escaped_parts` immediately before the function joins it and "
    "returns? Return exactly the key in the template."
)


TEMPLATE_ANSWER = {"escaped_parts": ["str"]}


def extract_trace_local(trace_log: Path, func_name: str, variable_name: str):
    selected_line = None
    marker = f" {func_name} event=return"
    for line in trace_log.read_text(encoding="utf-8").splitlines():
        if marker in line and " locals=" in line:
            selected_line = line
    if selected_line is None:
        raise RuntimeError(f"return trace for {func_name} not found in {trace_log}")

    locals_text = selected_line.split(" locals=", 1)[1]
    locals_dict = ast.literal_eval(locals_text)
    return ast.literal_eval(locals_dict[variable_name])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    oracle = {
        "question_kind": "S4_ProgramState",
        "question": QUESTION,
        "template_answer": TEMPLATE_ANSWER,
        "oracle_answer": {
            "escaped_parts": extract_trace_local(
                Path(args.trace_log),
                "reflex.utils.format._escape_js_string",
                "escaped_parts",
            )
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(oracle, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps(oracle, indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
