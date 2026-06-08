#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/layout/tree\.py):(?P<lineno>\d+) "
    r"(?P<func>libqtile\.layout\.tree\.(?:TreeNode\.)?get_next_window) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find TreeNode.get_next_window return events in trace log.")

    # The test triggers one relevant next() navigation; use the last match.
    target = matches[-1]
    locals_dict = ast.literal_eval(target.group("locals"))

    if "idx" not in locals_dict or "i" not in locals_dict:
        raise ValueError("Expected loop variables `idx` and `i` in return locals.")

    idx = int(str(locals_dict["idx"]))
    i = int(str(locals_dict["i"]))

    return {"loop_variable_state": {"idx": idx, "i": i}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/treetab_indirect_get_next_window_loop_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/treetab_indirect_get_next_window_loop_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `tests/qa/treetab_indirect_get_next_window_loop_state_test.py`, class "
            "`TestTreeTabIndirectGetNextWindowLoopStateQA`, method "
            "`test_treetab_indirect_get_next_window_loop_state_case`. "
            "The test builds a `TreeTab` hierarchy by applying several tree mutation commands, "
            "then sets focus to window `J` and calls `layout.next()`. "
            "This is indirect testing: `TreeTab.next` calls `self._nodes[self._focused].get_next_window()` "
            "from `libqtile/layout/tree.py`. In `TreeNode.get_next_window`, inside the `while` + `for` "
            "search path, the function returns via the `if res:` branch. At that return point, "
            "what are the exact values of loop variables `idx` and `i`?"
        ),
        "template_answer": {
            "loop_variable_state": {"idx": "int", "i": "int"}
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
