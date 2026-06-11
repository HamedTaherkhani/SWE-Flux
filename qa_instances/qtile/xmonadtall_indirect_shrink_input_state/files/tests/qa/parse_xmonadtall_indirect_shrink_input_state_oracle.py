#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/layout/xmonad\.py):(?P<lineno>\d+) "
    r"(?P<func>libqtile\.layout\.xmonad\.(?:MonadTall\.)?_shrink) "
    r"event=call locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

TARGET_CALL_INDEX = 11  # 1-based


def extract_output(trace_text: str) -> dict:
    matches = list(CALL_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find MonadTall._shrink call events in trace log.")

    if len(matches) < TARGET_CALL_INDEX:
        raise ValueError(
            f"Expected at least {TARGET_CALL_INDEX} _shrink calls, found {len(matches)}."
        )

    target = matches[TARGET_CALL_INDEX - 1]
    locals_dict = ast.literal_eval(target.group("locals"))

    cidx = int(locals_dict["cidx"])
    amt = float(locals_dict["amt"])
    return {"input_state": {"cidx": cidx, "amt": amt}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/xmonadtall_indirect_shrink_input_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/xmonadtall_indirect_shrink_input_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `tests/qa/xmonadtall_indirect_shrink_input_state_test.py`, class "
            "`TestXMonadTallIndirectShrinkInputStateQA`, method "
            "`test_xmonadtall_indirect_shrink_input_state_case`. "
            "The test calls `layout.grow()` on a `MonadTall` instance after setting "
            "`change_size=37`, `min_secondary_size=77`, `screen_rect.height=913`, "
            "focus index `3`, and initial `relative_sizes=[0.19, 0.27, 0.21, 0.33]`. "
            "This is indirect testing: `grow()` calls `_grow_secondary()`, which calls "
            "`shrink_up_shared()`/`shrink_down_shared()`, which then call `_shrink(cidx, amt)`. "
            "At the 11th call to `MonadTall._shrink` during this single test run (entry line in "
            "`libqtile/layout/xmonad.py`), what are the exact input values of `cidx` and `amt`?"
        ),
        "template_answer": {
            "input_state": {"cidx": "int", "amt": "float"},
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
