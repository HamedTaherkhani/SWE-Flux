#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Trace lines from shared/trace_plugin.py:
#   TIMESTAMP PATH:LINE mod.func event=call|return|exception ...
EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/faker/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|return|exception) ",
    re.MULTILINE,
)


def extract_max_depth(trace_text: str) -> dict[str, int]:
    depth = 0
    max_depth = 0
    for match in EVENT_RE.finditer(trace_text):
        event = match.group("event")
        if event == "call":
            depth += 1
            if depth > max_depth:
                max_depth = depth
        elif event in {"return", "exception"}:
            depth = max(0, depth - 1)
    if max_depth == 0:
        raise ValueError("No faker-scoped call/return events matched in trace log.")
    return {"maximum_call_stack_depth": max_depth}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/faker_chained_pystruct_pydict_parse_max_call_depth/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/faker_chained_pystruct_pydict_parse_max_call_depth/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_max_depth(trace_text)

    execution = (
        "from faker import Faker\n"
        "Faker.seed(13579)\n"
        "fake = Faker()\n"
        "fake.set_arguments('n', {'min_value': 1, 'max_value': 3})\n"
        "fake.pystruct(count=4, value_types=(str, dict, list, int))\n"
        "fake.pydict(nb_elements=5, variable_nb_elements=False, value_types=(str, float))\n"
        "fake.parse('{{ pyint:n }} {{ name }} {{ hex_color }}')\n"
    )

    qa = {
        "question_kind": "S2_InterProceduralCFG",
        "question": (
            "Use `faker_qa/faker_chained_pystruct_pydict_parse_max_call_depth/files/testcase.py`, class "
            "`TestFakerChainedPystructPydictParseMaxCallDepthQA`, method "
            "`test_faker_chained_pystruct_pydict_parse_max_call_depth_case`. "
            "In one test run it executes, in order: `set_arguments('n', ...)`, "
            "`pystruct(count=4, value_types=(str, dict, list, int))`, "
            "`pydict(nb_elements=5, variable_nb_elements=False, value_types=(str, float))`, "
            "and `parse('{{ pyint:n }} {{ name }} {{ hex_color }}')` after `Faker.seed(13579)`. "
            "The trace records `call` and `return` events **only** for code under `/testbed/faker/` "
            "(see `TRACE_FILE` in the instance `eval.sh`). "
            "Following the same stack-depth accounting as the Sympy `maximum_call_stack_depth` "
            "benchmarks (increment on each traced `call`, decrement on each traced `return` or "
            "`exception`), what is the **maximum** call stack depth reached at any point while "
            "processing this entire test?"
        ),
        "template_answer": {"maximum_call_stack_depth": "int"},
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
