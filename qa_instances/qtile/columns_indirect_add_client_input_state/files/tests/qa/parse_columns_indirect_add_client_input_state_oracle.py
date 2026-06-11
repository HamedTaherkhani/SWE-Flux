#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/libqtile/layout/columns\.py):(?P<lineno>\d+) "
    r"(?P<func>libqtile\.layout\.columns\.(?:_Column\.)?add_client) "
    r"event=call locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

TARGET_LINENO = 60
CLIENT_RE = re.compile(r"^DummyWin\((?P<name>[^)]+)\)$")


def extract_output(trace_text: str) -> dict:
    matches = [m for m in CALL_RE.finditer(trace_text) if int(m.group("lineno")) == TARGET_LINENO]
    if not matches:
        raise ValueError("Could not find _Column.add_client call events in trace log.")

    # The last _Column.add_client call is the one reached via layout.shuffle_right().
    target = matches[-1]
    locals_dict = ast.literal_eval(target.group("locals"))

    client_raw = str(locals_dict["client"])
    height = int(locals_dict["height"])

    match = CLIENT_RE.match(client_raw)
    client_name = match.group("name") if match else client_raw

    return {"input_state": {"client_name": client_name, "height": height}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/columns_indirect_add_client_input_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/columns_indirect_add_client_input_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `tests/qa/columns_indirect_add_client_input_state_test.py`, class "
            "`TestColumnsIndirectAddClientInputStateQA`, method "
            "`test_columns_indirect_add_client_input_state_case`. "
            "The test builds a `Columns` layout, adds 8 windows, then performs the mutation "
            "sequence `grow_up`, `grow_up`, `grow_down`, `shuffle_up`, `grow_down`, and finally "
            "calls `layout.shuffle_right()`. This is indirect testing: inside "
            "`libqtile/layout/columns.py`, `Columns.shuffle_right` calls `add_column`, then calls "
            "`_Column.add_client(client, cur.heights[client])` (method defined at line 60). "
            "At that `_Column.add_client` entry during the final `shuffle_right` call, what are "
            "the exact input values of `client_name` and `height`?"
        ),
        "template_answer": {
            "input_state": {"client_name": "str", "height": "int"}
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
