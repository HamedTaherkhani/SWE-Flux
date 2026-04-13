#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)
def _parse_scalar(value_repr: str):
    try:
        return ast.literal_eval(value_repr)
    except Exception:
        return value_repr


def extract_path(trace_text: str) -> dict[str, object]:
    origin = tag = version = None

    for m in LINE_RE.finditer(trace_text):
        if not m.group("func").endswith("._make_label"):
            continue
        locals_map = ast.literal_eval(m.group("locals"))
        if origin is None and "origin" in locals_map:
            origin = _parse_scalar(locals_map["origin"])
        if tag is None and "tag" in locals_map:
            tag = _parse_scalar(locals_map["tag"])
        if version is None and "version" in locals_map:
            version = _parse_scalar(locals_map["version"])

    if origin is None or tag is None:
        raise ValueError("Could not capture _make_label inputs from trace.")

    executed_path: list[str] = []
    if tag != version:
        executed_path.append("tag_not_equal_version")
        if version:
            executed_path.append("version_truthy_return_build_label")
        else:
            executed_path.append("version_falsy_return_origin_tag")
    else:
        executed_path.append("tag_equal_version")
        if origin == "yt-dlp/yt-dlp":
            executed_path.append("channel_mapping_found_return_channel_label")
        else:
            executed_path.append("channel_mapping_missing_return_origin_tag")

    return {"executed_path": executed_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/make_label_execution_path/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/make_label_execution_path/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_path(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `test/qa/make_label_execution_path_test.py`, class "
            "`TestMakeLabelExecutionPathQA`, method "
            "`test_make_label_execution_path_case`. In `yt_dlp/update.py::_make_label`, "
            "for input `(origin='yt-dlp/yt-dlp', tag='2024.01.01', version='2024.01.01')`, "
            "what exact control-flow path is executed through the function's branch structure? "
            "Return `executed_path` as an ordered list of branch-decision labels."
        ),
        "template_answer": {
            "executed_path": ["str"],
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
