from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


QUESTION = (
    "Use `tests/qa/utils_format_lcs_max_length_loop_state_test.py`, class "
    "`TestUtilsFormatLcsMaxLengthLoopStateQA`, method "
    "`test_utils_format_lcs_max_length_loop_state_case`. The test directly calls "
    "`length_of_largest_common_substring(str1, str2)` at "
    "`tests/qa/utils_format_lcs_max_length_loop_state_test.py:17`. The target "
    "function is `reflex.utils.format.length_of_largest_common_substring`, defined "
    "at `reflex/utils/format.py:30`. In that function, local variable `max_length` "
    "is initialized at `reflex/utils/format.py:47`, then updated inside the nested "
    "`for i` / `for j` loops and the conditional `if dp[i][j] > max_length` at "
    "`reflex/utils/format.py:50-55`, before being returned at "
    "`reflex/utils/format.py:57`. What is the exact final state of the single "
    "target variable `max_length` when the function returns? Return exactly the "
    "key in the template."
)


TEMPLATE_ANSWER = {"max_length": "int"}


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
        "question_kind": "program_state_prediction",
        "question": QUESTION,
        "template_answer": TEMPLATE_ANSWER,
        "oracle_answer": {
            "max_length": extract_trace_local(
                Path(args.trace_log),
                "reflex.utils.format.length_of_largest_common_substring",
                "max_length",
            )
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(oracle, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps(oracle, indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
