#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/reflex/components/(?:core/foreach|tags/iter_tag|component)\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)

ALLOWED_FUNCS = {
    "reflex.components.core.foreach.Foreach.create",
    "reflex.components.core.foreach.Foreach._render",
    "reflex.components.core.foreach.Foreach.render",
    "reflex.components.tags.iter_tag.IterTag.render_component",
    "reflex.components.tags.iter_tag.IterTag.get_arg_var",
    "reflex.components.tags.iter_tag.IterTag.get_index_var",
    "reflex.components.tags.iter_tag.IterTag.get_arg_var_arg",
    "reflex.components.tags.iter_tag.IterTag.get_index_var_arg",
    "reflex.components.tags.iter_tag.IterTag.get_iterable_var_type",
    "reflex.components.component.Component.create",
    "reflex.components.component.Component._create",
}


def extract_execution_path(trace_text: str) -> dict:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find line events for execution path extraction.")

    executed_path = []
    for match in matches:
        func = match.group("func")
        if func not in ALLOWED_FUNCS:
            continue
        executed_path.append(
            {
                "file": match.group("path").replace("/testbed/", ""),
                "func": func,
                "line": int(match.group("lineno")),
            }
        )
    if not executed_path:
        raise ValueError("Trace had line events, but none matched the exact target functions.")
    return {"executed_path": executed_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/components_foreach_render_execution_path_lines/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/components_foreach_render_execution_path_lines/oracle.json",
    )
    args = parser.parse_args()

    output = extract_execution_path(Path(args.trace_log).read_text(encoding="utf-8"))
    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "question": (
            "Use `tests/qa/components_foreach_render_execution_path_lines_test.py`, class "
            "`TestComponentsForeachRenderExecutionPathLinesQA`, method "
            "`test_components_foreach_render_execution_path_lines_case`. "
            "At line 24, the test calls `rx.foreach(rows, render_row)` after constructing `rows` at lines 19-22; "
            "at line 25 it calls `component.render()`. Return the execution path only for line events in files "
            "`reflex/components/core/foreach.py`, `reflex/components/tags/iter_tag.py`, and "
            "`reflex/components/component.py`, and only for these functions: "
            "`reflex.components.core.foreach.Foreach.create`, `reflex.components.core.foreach.Foreach._render`, "
            "`reflex.components.core.foreach.Foreach.render`, `reflex.components.tags.iter_tag.IterTag.render_component`, "
            "`reflex.components.tags.iter_tag.IterTag.get_arg_var`, `reflex.components.tags.iter_tag.IterTag.get_index_var`, "
            "`reflex.components.tags.iter_tag.IterTag.get_arg_var_arg`, "
            "`reflex.components.tags.iter_tag.IterTag.get_index_var_arg`, "
            "`reflex.components.tags.iter_tag.IterTag.get_iterable_var_type`, "
            "`reflex.components.component.Component.create`, and `reflex.components.component.Component._create`. "
            "This execution creates a foreach component, renders a representative child through `render_row`, "
            "sets a key from the index var, and renders the foreach tag. What is the exact ordered execution path "
            "as a list of objects with keys `file`, `func`, and `line`, including repeated lines?"
        ),
        "template_answer": {
            "executed_path": [{"file": "str", "func": "str", "line": "int"}]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
