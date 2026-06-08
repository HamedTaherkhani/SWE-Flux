#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TARGET_FUNC = "reflex.components.component.Component.render"
CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/reflex/components/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call ",
    re.MULTILINE,
)


def extract_call_frequency(trace_text: str) -> dict:
    call_count = 0
    for match in CALL_RE.finditer(trace_text):
        if match.group("func") == TARGET_FUNC:
            call_count += 1
    return {"function_call_count": call_count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/components_nested_render_call_frequency/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/components_nested_render_call_frequency/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_call_frequency(trace_text)

    qa = {
        "question_kind": "S2_InterProceduralCFG",
        "question": (
            "Use `tests/qa/components_nested_render_call_frequency_test.py`, class "
            "`TestComponentsNestedRenderCallFrequencyQA`, method "
            "`test_components_nested_render_call_frequency_case`. The nested `dashboard` component tree is "
            "constructed at lines 8-25, and line 27 executes `rendered = dashboard.render()`. "
            "During this test run, how many times is function "
            "`reflex.components.component.Component.render` in file `reflex/components/component.py` called?"
        ),
        "template_answer": {
            "function_call_count": "int"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
