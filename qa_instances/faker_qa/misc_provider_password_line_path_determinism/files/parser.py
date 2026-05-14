#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/faker/providers/misc/__init__.py"
TARGET_FUNCS = {
    "faker.providers.misc.password",
    "faker.providers.misc.Provider.password",
}

START_RE = re.compile(r"\[TRACE\]\[START\]")
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/faker/providers/misc/__init__\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception)\b"
)


def extract_sequences(trace_text: str) -> list[list[int]]:
    sequences: list[list[int]] = []
    current: list[int] = []
    started = False

    for raw_line in trace_text.splitlines():
        if START_RE.search(raw_line):
            if started:
                sequences.append(current)
                current = []
            else:
                started = True
            continue

        if not started:
            continue

        m = LINE_RE.match(raw_line)
        if not m:
            continue
        if m.group("path") != TARGET_PATH:
            continue
        if m.group("func") not in TARGET_FUNCS:
            continue
        if m.group("event") != "line":
            continue
        current.append(int(m.group("lineno")))

    if started:
        sequences.append(current)

    return sequences


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/faker_qa/misc_provider_password_line_path_determinism/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/faker_qa/misc_provider_password_line_path_determinism/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    sequences = extract_sequences(trace_text)

    invariant_exists = (
        len(sequences) == 10
        and all(seq for seq in sequences)
        and all(seq == sequences[0] for seq in sequences[1:])
    )

    execution = (
        "from faker import Faker\n"
        "Faker.seed(20260403)\n"
        "fake = Faker()\n"
        "fake.password(\n"
        "    length=24,\n"
        "    special_chars=True,\n"
        "    digits=True,\n"
        "    upper_case=True,\n"
        "    lower_case=True,\n"
        ")\n"
    )

    qa = {
        "question_kind": "M1_IntraProceduralCFG",
        "question": (
            "Execute "
            "`faker_qa/misc_provider_password_line_path_determinism/files/testcase.py::"
            "TestMiscProviderPasswordLinePathDeterminismQA::"
            "test_misc_provider_password_line_path_determinism_case` exactly 10 "
            "independent times with identical inputs. In each execution, focus on "
            "`faker/providers/misc/__init__.py`, the `Provider.password` implementation "
            "(traced as `faker.providers.misc.password` in line-trace output on CPython 3.10). "
            "The method builds `required_tokens` from conditional `random.choice` draws over "
            "expanding `choices` pools, asserts length feasibility, then enters a `while True` "
            "loop that repeatedly samples characters, shuffles, and validates category coverage "
            "until all constraints are met—so the dynamic control flow is coupled to the shared "
            "`Generator.random` stream after `Faker.seed(...)`. "
            "Do repeated runs follow the exact same sequence of executed **line numbers** "
            "inside this target function (line events only)? "
            "Return JSON with exactly one key: `{\"invariant_exists\": <bool>}`."
        ),
        "template_answer": {
            "invariant_exists": "bool",
        },
        "oracle_answer": {
            "invariant_exists": invariant_exists,
        },
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
