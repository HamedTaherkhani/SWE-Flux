#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

_PATTERN_MARKER = "'pattern': \"'"
_PATTERN_END = "'\""

# Second chronological `cellphone_number` completion in the testcase.
TARGET_RETURN_INDEX = 2


def _extract_pattern_from_return_line(line: str) -> str:
    idx = line.find(_PATTERN_MARKER)
    if idx < 0:
        raise ValueError(f"Could not find pattern marker in trace line: {line!r}")
    start = idx + len(_PATTERN_MARKER)
    end = line.find(_PATTERN_END, start)
    if end < 0:
        raise ValueError(f"Could not find pattern terminator in trace line: {line!r}")
    return line[start:end]


def extract_output(trace_text: str) -> dict[str, str]:
    lines = []
    for line in trace_text.splitlines():
        if "faker.providers.phone_number.ar_AE.cellphone_number" not in line:
            continue
        if " event=return " not in line:
            continue
        lines.append(line)

    if len(lines) < TARGET_RETURN_INDEX:
        raise ValueError(
            f"Expected at least {TARGET_RETURN_INDEX} cellphone_number return events, "
            f"found {len(lines)}.",
        )

    pattern = _extract_pattern_from_return_line(lines[TARGET_RETURN_INDEX - 1])
    return {"pattern": pattern}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/phone_number_ar_ae_cellphone_pattern_internal_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/phone_number_ar_ae_cellphone_pattern_internal_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "fake = Faker('ar_AE')\n"
        "fake.seed_instance(2026)\n"
        "fake.phone_number()\n"
        "fake.cellphone_number()\n"
        "fake.telephone_number()\n"
        "fake.cellphone_number()\n"
    )

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `faker_qa/phone_number_ar_ae_cellphone_pattern_internal_state/files/testcase.py`, class "
            "`TestPhoneNumberArAeCellphonePatternInternalStateQA`, method "
            "`test_phone_number_ar_ae_cellphone_pattern_internal_state_case`. In that test, line 11 constructs "
            "`Faker('ar_AE')`, line 12 calls `seed_instance(2026)`, line 13 calls `phone_number()` (which samples "
            "from the large combined `formats` tuple mixing cellphone, telephone, toll, and service templates), "
            "line 14 calls `cellphone_number()`, line 15 calls `telephone_number()`, and line 16 calls "
            "`cellphone_number()` "
            "again. Inside `faker/providers/phone_number/ar_AE/__init__.py::Provider.cellphone_number` "
            "(lines 76-78), `pattern` is assigned from `random_element(self.cellphone_formats)` before "
            "`numerify(generator.parse(pattern))`. This is a **Variable State (Internal)** task: for the "
            "**second** chronological `return` event from `cellphone_number` in this run, what is the "
            "exact string value held by the local variable `pattern` at that return (the raw format template "
            "before parsing, not the final numerified phone string)?"
        ),
        "template_answer": {
            "pattern": "str",
        },
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
