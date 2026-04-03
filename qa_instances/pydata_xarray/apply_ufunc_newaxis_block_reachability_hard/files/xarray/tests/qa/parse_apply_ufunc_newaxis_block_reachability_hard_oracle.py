#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>[^ ]+) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _parse_old_dims(locals_map: dict) -> tuple[str, ...] | None:
    raw = locals_map.get("old_dims")
    if raw is None:
        return None
    try:
        value = ast.literal_eval(raw)
    except Exception:
        return None
    return tuple(value) if isinstance(value, tuple) else None


def extract_reachability(trace_text: str) -> dict[str, bool]:
    matches = []
    for m in RETURN_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        func = m.group("func")
        if not path.endswith("/xarray/tests/qa/apply_ufunc_newaxis_block_reachability_hard_test.py"):
            continue
        if not func.endswith(".test_apply_ufunc_newaxis_block_reachability_hard_case"):
            continue
        matches.append(m)
    if not matches:
        raise ValueError("Could not find target test return event in trace log.")

    locals_map = ast.literal_eval(matches[-1].group("locals"))
    if "observed_target_block_executed" not in locals_map:
        raise ValueError("Missing observed_target_block_executed in test locals.")
    value = ast.literal_eval(locals_map["observed_target_block_executed"])
    if not isinstance(value, bool):
        raise ValueError("observed_target_block_executed is not a bool.")
    return {"target_block_executed": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/apply_ufunc_newaxis_block_reachability_hard/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/apply_ufunc_newaxis_block_reachability_hard/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_reachability(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `xarray/tests/qa/apply_ufunc_newaxis_block_reachability_hard_test.py`, class "
            "`TestApplyUfuncNewaxisBlockReachabilityHardQA`, method "
            "`test_apply_ufunc_newaxis_block_reachability_hard_case`. "
            "At line 27, `xr.apply_ufunc(...)` combines inputs with dims `('x', 'y')` and `('z', 'y')` "
            "using `input_core_dims=[['y'], ['y']]`. For this exact run, determine whether the "
            "`np.newaxis` insertion branch in broadcast alignment logic (the block equivalent to "
            "`elif key_parts: key_parts.append(np.newaxis)`) is executed."
        ),
        "template_answer": {
            "target_block_executed": "bool"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
