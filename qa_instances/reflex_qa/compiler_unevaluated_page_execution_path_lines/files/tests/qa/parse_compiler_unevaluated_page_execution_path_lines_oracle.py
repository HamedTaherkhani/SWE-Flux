#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/reflex/(?:compiler/(?:compiler|utils)\.py|components/component\.py)):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)

ALLOWED_FUNCS = {
    "reflex.compiler.compiler.compile_unevaluated_page",
    "reflex.components.component.Component._has_stateful_event_triggers",
    "reflex.components.component.Component._event_trigger_values_use_state",
    "reflex.compiler.utils.add_meta",
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
        default="/testbed/logs/qa_instances/compiler_unevaluated_page_execution_path_lines/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/compiler_unevaluated_page_execution_path_lines/oracle.json",
    )
    args = parser.parse_args()

    output = extract_execution_path(Path(args.trace_log).read_text(encoding="utf-8"))
    qa = {
        "question_kind": "C2_InterProceduralCFG",
        "question": (
            "Use `tests/qa/compiler_unevaluated_page_execution_path_lines_test.py`, class "
            "`TestCompilerUnevaluatedPageExecutionPathLinesQA`, method "
            "`test_compiler_unevaluated_page_execution_path_lines_case`. "
            "At lines 52-61, the test calls `compile_unevaluated_page(...)` on the `UnevaluatedPage` "
            "constructed at lines 42-50 from `compiler_path_page`. Return the execution path only for line events "
            "in files `reflex/compiler/compiler.py`, `reflex/compiler/utils.py`, and `reflex/components/component.py`, "
            "and only for these functions: `reflex.compiler.compiler.compile_unevaluated_page`, "
            "`reflex.components.component.Component._has_stateful_event_triggers`, "
            "`reflex.components.component.Component._event_trigger_values_use_state`, "
            "and `reflex.compiler.utils.add_meta`. "
            "This path includes nested page component creation, recursive event-trigger checks that find a stateful "
            "button handler, and metadata injection. What is the exact ordered execution path as a list of objects with keys "
            "`file`, `func`, and `line`, including repeated lines?"
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
