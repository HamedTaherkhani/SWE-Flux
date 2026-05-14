#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

_PATTERN_MARKER = "'pattern': \"'"
_PATTERN_END = "'\""


def extract_output(trace_text: str) -> dict[str, str]:
    lines = []
    for line in trace_text.splitlines():
        if "faker.providers.address.en_GB.postcode" not in line:
            continue
        if " event=return " not in line:
            continue
        lines.append(line)

    if not lines:
        raise ValueError("Could not find en_GB.postcode return events in trace log.")

    target_line = lines[-1]
    idx = target_line.find(_PATTERN_MARKER)
    if idx < 0:
        raise ValueError(f"Could not find pattern marker in trace line: {target_line!r}")
    start = idx + len(_PATTERN_MARKER)
    end = target_line.find(_PATTERN_END, start)
    if end < 0:
        raise ValueError(f"Could not find pattern terminator in trace line: {target_line!r}")

    return {"postcode_pattern": target_line[start:end]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/address_en_gb_postcode_pattern_internal_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/address_en_gb_postcode_pattern_internal_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "fake = Faker('en_GB')\n"
        "fake.seed_instance(246810)\n"
        "fake.city()\n"
        "fake.street_name()\n"
        "fake.postcode()\n"
    )

    qa = {
        "question_kind": "C4_ProgramState",
        "question": (
            "Use `faker_qa/address_en_gb_postcode_pattern_internal_state/files/testcase.py`, class "
            "`TestAddressEnGbPostcodePatternInternalStateQA`, method "
            "`test_address_en_gb_postcode_pattern_internal_state_case`. In that test, line 11 constructs "
            "`Faker('en_GB')`, line 12 calls `seed_instance(246810)`, line 13 calls `city()`, line 14 calls "
            "`street_name()`, and line 15 calls `postcode()`. In `faker/providers/address/en_GB/__init__.py`, "
            "`postcode` (lines 530-539) initializes `postcode = \"\"`, draws `pattern = self.random_element("
            "self.postcode_formats)`, then iterates `for placeholder in pattern` appending from "
            "instance `self` into `postcode` using class-level `_postcode_sets`. This is a "
            "**Class Methods/Variable States** task: at the traced final `return` from that `postcode()` "
            "call on the `en_GB` provider, what is the **exact** string value of the local variable `pattern` "
            "(the template selected from `postcode_formats` **before** placeholder expansion), rather than the "
            "fully expanded outward postcode string?"
        ),
        "template_answer": {
            "postcode_pattern": "str",
        },
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
