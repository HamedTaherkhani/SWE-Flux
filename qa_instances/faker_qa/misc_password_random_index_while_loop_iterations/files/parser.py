#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/faker/providers/misc/__init__.py"
TARGET_FUNC = "faker.providers.misc.password"
WHILE_BODY_LINE = 206

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/faker/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)


def count_while_body_iterations(trace_text: str) -> int:
    """Count executions of the while-loop body line (randint into the set) for the
    top-level `password` invocation only (depth 1), matching the Sympy dpll pattern.
    """
    depth = 0
    count = 0

    for line in trace_text.splitlines():
        m = EVENT_RE.match(line)
        if not m:
            continue

        path = m.group("path")
        func = m.group("func")
        event = m.group("event")
        lineno = int(m.group("lineno"))

        if path != TARGET_PATH or func != TARGET_FUNC:
            continue

        if event == "call":
            depth += 1
            continue

        if event in {"return", "exception"}:
            depth = max(0, depth - 1)
            continue

        if event == "line" and depth == 1 and lineno == WHILE_BODY_LINE:
            count += 1

    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/misc_password_random_index_while_loop_iterations/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/misc_password_random_index_while_loop_iterations/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    iteration_count = count_while_body_iterations(trace_text)

    qa = {
        "question_kind": "C3_Loops",
        "question": (
            "Use `faker_qa/misc_password_random_index_while_loop_iterations/files/testcase.py`, class "
            "`TestMiscPasswordRandomIndexWhileLoopIterationsQA`, method "
            "`test_misc_password_random_index_while_loop_iterations_case`. "
            "The test constructs a `Faker` instance, calls `seed_instance(777888999)`, then "
            "`password(length=8, special_chars=True, digits=True, upper_case=True, lower_case=True)`. "
            "That dispatches through the proxy to `faker.providers.misc.Provider.password` "
            "(localized subclasses share the same implementation in `faker/providers/misc/__init__.py`). "
            "In that function, consider the loop `while len(random_indexes) < len(required_tokens):` "
            "at line `205` whose body is line `206` "
            "(`random_indexes.add(self.generator.random.randint(0, len(chars) - 1))`). "
            "Duplicate index draws do not grow the set, so the loop may execute more than "
            "`len(required_tokens)` times. "
            "How many times does line `206` execute during this test run in the **top-level** "
            "invocation of `password` (i.e., not counting any nested or unrelated calls)? "
            "Return a JSON object with key `loop_iteration_count` and integer value."
        ),
        "template_answer": {
            "loop_iteration_count": "int",
        },
        "oracle_answer": {
            "loop_iteration_count": iteration_count,
        },
        "execution": (
            "from faker import Faker\n"
            "fake = Faker()\n"
            "fake.seed_instance(777888999)\n"
            "fake.password(\n"
            "    length=8,\n"
            "    special_chars=True,\n"
            "    digits=True,\n"
            "    upper_case=True,\n"
            "    lower_case=True,\n"
            ")\n"
        ),
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
