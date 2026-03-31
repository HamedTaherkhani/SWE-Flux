#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

TARGET_FUNC_QUAL = "faker.providers.profile.profile"
VAR_NAME = "d"

def extract_temporal_values(trace_text: str) -> list[str]:
    temporal_values = []
    
    for line in trace_text.splitlines():
        if "event=line" not in line:
            continue
        if TARGET_FUNC_QUAL not in line:
            continue
            
        # extract locals part
        locals_idx = line.find("locals=")
        if locals_idx == -1:
            continue
            
        locals_str = line[locals_idx + 7:]
        try:
            locs = ast.literal_eval(locals_str)
            if VAR_NAME in locs:
                # Remove extra trailing spaces or differences from the dict repr
                temporal_values.append(locs[VAR_NAME])
        except Exception as e:
            pass

    return temporal_values

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/profile_temporal_value_history_d/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/profile_temporal_value_history_d/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    observed_values = extract_temporal_values(trace_text)

    qa = {
        "question_kind": "data_flow_prediction",
        "question": (
            "Use `testcase.py`, class "
            "`TestProfileTemporalValueHistoryDQA`, method "
            "`test_profile_temporal_value_history_d_case`. "
            "Focus only on function `faker.providers.profile.profile` "
            "in file `faker/providers/profile/__init__.py`. "
            f"Track exactly the variable: `{VAR_NAME}`. "
            "List the ordered sequence of all values assigned to this variable during the execution of this test. "
            "Return the answer as `temporal_value_history`, a list of strings representing the stringified values of the variable in chronological assignment order."
        ),
        "template_answer": {
            "temporal_value_history": [
                "str"
            ]
        },
        "oracle_answer": {
            "temporal_value_history": observed_values,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
