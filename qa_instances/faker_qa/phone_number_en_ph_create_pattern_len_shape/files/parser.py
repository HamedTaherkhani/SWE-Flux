#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

# Trace locals render string values as `"'<body>'"` after the `'pattern': ` key prefix.
_PATTERN_MARKER = "'pattern': \"'"
_PATTERN_END = "'\""

# 1-based index into chronological `_create_phone_number` return events for this testcase.
TARGET_RETURN_INDEX = 6


def extract_output(trace_text: str) -> dict[str, int]:
    lines = []
    for line in trace_text.splitlines():
        if "faker.providers.phone_number.en_PH._create_phone_number" not in line:
            continue
        if " event=return " not in line:
            continue
        lines.append(line)

    if len(lines) < TARGET_RETURN_INDEX:
        raise ValueError(
            f"Expected at least {TARGET_RETURN_INDEX} _create_phone_number return events, "
            f"found {len(lines)}.",
        )

    target_line = lines[TARGET_RETURN_INDEX - 1]
    idx = target_line.find(_PATTERN_MARKER)
    if idx < 0:
        raise ValueError(f"Could not find pattern marker in trace line: {target_line!r}")
    start = idx + len(_PATTERN_MARKER)
    end = target_line.find(_PATTERN_END, start)
    if end < 0:
        raise ValueError(f"Could not find pattern terminator in trace line: {target_line!r}")

    pattern = target_line[start:end]
    return {"pattern_char_len": len(pattern)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/phone_number_en_ph_create_pattern_len_shape/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/phone_number_en_ph_create_pattern_len_shape/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "fake = Faker('en_PH')\n"
        "fake.seed_instance(1337)\n"
        "fake.mobile_number()\n"
        "fake.globe_mobile_number()\n"
        "fake.sun_mobile_number()\n"
        "fake.smart_mobile_number()\n"
        "fake.pldt_area2_landline_number()\n"
        "fake.misc_area2_landline_number()\n"
        "fake.non_area2_landline_number()\n"
    )

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `faker_qa/phone_number_en_ph_create_pattern_len_shape/files/testcase.py`, class "
            "`TestPhoneNumberEnPhCreatePatternLenShapeQA`, method "
            "`test_phone_number_en_ph_create_pattern_len_shape_case`. In that test, line 12 calls "
            "`seed_instance(1337)`, then lines 13-19 invoke seven different `en_PH` helpers (`mobile_number`, "
            "`globe_mobile_number`, `sun_mobile_number`, `smart_mobile_number`, `pldt_area2_landline_number`, "
            "`misc_area2_landline_number`, `non_area2_landline_number`). Each helper funnels into "
            "`faker/providers/phone_number/en_PH/__init__.py::Provider._create_phone_number` (defined at line 199), "
            "which samples `pattern = self.random_element(formats)` before `numerify(generator.parse(pattern))`. "
            "This is a **Type and Shape** prediction task: for the **sixth** chronological `return` event from "
            "`_create_phone_number` during this run, what is the exact integer value of `len(pattern)` for the "
            "`pattern` local at that return (equivalently, the character length of the chosen format template "
            "string before parsing/numerification)?"
        ),
        "template_answer": {
            "pattern_char_len": "int",
        },
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
