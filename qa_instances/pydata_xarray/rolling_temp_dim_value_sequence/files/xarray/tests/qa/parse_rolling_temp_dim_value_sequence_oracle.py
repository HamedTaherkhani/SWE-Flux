#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)"
    r"(?: .*?locals=(?P<locals>\{.*\}))?$",
    re.MULTILINE,
)


def _parse_new_dim(locals_text: str | None) -> str | None:
    if not locals_text:
        return None
    try:
        locals_map = ast.literal_eval(locals_text)
    except Exception:
        return None
    if not isinstance(locals_map, dict) or "new_dim" not in locals_map:
        return None
    raw = locals_map["new_dim"]
    try:
        value = ast.literal_eval(raw)
    except Exception:
        return None
    return value if isinstance(value, str) else None


def extract_value_sequence(trace_text: str) -> dict[str, list[str]]:
    active = False
    seq: list[str] = []

    for m in EVENT_RE.finditer(trace_text):
        func = m.group("func")
        event = m.group("event")
        if not func.endswith(".get_temp_dimname"):
            continue

        if event == "call":
            nd = _parse_new_dim(m.group("locals"))
            if nd == "_rolling_dim_x" and not active:
                active = True
                seq = [nd]
            continue

        if active and event == "line":
            nd = _parse_new_dim(m.group("locals"))
            if nd is not None and (not seq or nd != seq[-1]):
                seq.append(nd)
            continue

        if active and event in {"return", "exception"}:
            break

    if not seq:
        raise ValueError("Could not find target get_temp_dimname value sequence.")

    return {"assigned_value_sequence": seq}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/rolling_temp_dim_value_sequence/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/rolling_temp_dim_value_sequence/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_value_sequence(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `xarray/tests/qa/rolling_temp_dim_value_sequence_test.py`, class "
            "`TestRollingTempDimValueSequenceHardQA`, method "
            "`test_rolling_temp_dim_value_sequence_case`. "
            "At line 23, `.rolling(x=3, center=True, min_periods=1).reduce(np.sum)` is executed, which triggers "
            "`xarray/core/rolling.py` and calls `xarray/core/utils.py::get_temp_dimname` from the "
            "rolling-dimension setup for `x`. Focus on the first invocation where the incoming argument "
            "`new_dim` is `'_rolling_dim_x'`. Inside `get_temp_dimname`, `new_dim` is updated in a while-loop "
            "until unique. What is the ordered list of all values assigned to `new_dim` during that invocation?"
        ),
        "template_answer": {"assigned_value_sequence": ["str"]},
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
