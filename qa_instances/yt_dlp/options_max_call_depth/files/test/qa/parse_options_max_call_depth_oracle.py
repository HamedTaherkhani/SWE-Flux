#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def extract_max_depth(trace_text: str) -> dict[str, object]:
    # The trace filter is the test file, but the trace plugin's call/return pairing
    # can be noisy (e.g., generator frames). To make this stable, we compute depth
    # from the recursion parameter `n` in the test's local helper `recurse`.
    #
    # The maximum stack depth (within traced frames) occurs during the deepest
    # `recurse(n)` call. When the first `recurse` call is `n = N`, the number of
    # recursive frames is `N + 1` (down to n=0), plus the outer test method frame.
    max_n = None
    for line in trace_text.splitlines():
        if "options_max_call_depth_test.py" not in line:
            continue
        if " options_max_call_depth_test.recurse event=call " not in line:
            continue
        # locals includes `n`: '25' (as a repr string)
        if "locals=" not in line or "'n':" not in line:
            continue
        try:
            locals_part = line.split(" locals=", 1)[1]
            # crude extract: "'n': '25'," or "'n': '0',"
            after = locals_part.split("'n':", 1)[1].lstrip()
            # after starts with "'25'" or " '25'"
            if after[0] == "'":
                after = after[1:]
            n_str = after.split("'", 1)[0]
            n_val = int(n_str)
        except Exception:
            continue
        max_n = n_val if max_n is None else max(max_n, n_val)

    if max_n is None:
        return {"max_call_stack_depth": 0}

    return {"max_call_stack_depth": max_n + 2}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/options_max_call_depth/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/options_max_call_depth/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_max_depth(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `test/qa/options_max_call_depth_test.py`, class "
            "`TestOptionsMaxCallDepthQA`, method "
            "`test_options_max_call_depth_case`. Consider only trace lines whose `path` "
            "ends with `test/qa/options_max_call_depth_test.py` and only `event=call` and "
            "`event=return` events. What is the maximum dynamic call stack depth reached at any "
            "point during the test execution? Return the integer as "
            "`max_call_stack_depth`."
        ),
        "template_answer": {"max_call_stack_depth": "int"},
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
