#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|return|exception)"
    r"(?: .*?locals=(?P<locals>\{.*\}))?$",
    re.MULTILINE,
)


def _class_from_locals(locals_text: str | None) -> str | None:
    if not locals_text:
        return None
    if "PandasMultiIndex" in locals_text:
        return "PandasMultiIndex"
    if "PandasIndex" in locals_text:
        return "PandasIndex"
    if "Index" in locals_text:
        return "Index"
    return None


def extract_concrete_dispatch(trace_text: str) -> dict[str, str]:
    map_depth = 0
    seen_dispatches = 0

    for m in EVENT_RE.finditer(trace_text):
        func = m.group("func")
        event = m.group("event")

        if func.endswith(".map_index_queries"):
            if event == "call":
                map_depth += 1
            elif event in {"return", "exception"}:
                map_depth = max(map_depth - 1, 0)
            continue

        if event == "call":
            if map_depth > 0 and func.endswith(".sel"):
                seen_dispatches += 1
                if seen_dispatches == 2:
                    concrete = _class_from_locals(m.group("locals"))
                    if concrete is None:
                        raise ValueError(
                            "Found target sel dispatch, but could not infer concrete class from locals."
                        )
                    return {"concrete_class": concrete}

    raise ValueError("Could not find the second sel dispatch under map_index_queries.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/map_index_queries_concrete_sel_dispatch/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/map_index_queries_concrete_sel_dispatch/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_concrete_dispatch(trace_text)

    qa = {
        "question_kind": "S2_InterProceduralCFG",
        "question": (
            "Use `xarray/tests/qa/map_index_queries_concrete_sel_dispatch_test.py`, class "
            "`TestMapIndexQueriesConcreteSelDispatchHardQA`, method "
            "`test_map_index_queries_concrete_sel_dispatch_case`. "
            "This test executes `stacked.sel(time=slice(1, 3), cell={'lat': 'B'})` at line 24, "
            "which goes through `xarray/core/indexing.py::map_index_queries`. "
            "Inside `map_index_queries`, the statement `results.append(index.sel(labels, **options))` "
            "dispatches to concrete index implementations for each grouped index. "
            "For the second execution of that `index.sel(...)` call in this run, which concrete class's "
            "`sel` method is actually executed?"
        ),
        "template_answer": {"concrete_class": "str"},
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
