#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


def extract_output(trace_text: str) -> dict[str, int]:
    lines = []
    for line in trace_text.splitlines():
        if "faker.providers.doi.doi" not in line:
            continue
        if " event=return " not in line:
            continue
        lines.append(line)

    if not lines:
        raise ValueError("Could not find doi return events in trace log.")

    target_line = lines[-1]
    if "event=return retval=" not in target_line or " locals=" not in target_line:
        raise ValueError(f"Unexpected doi return line format: {target_line!r}")

    fragment = target_line.split("event=return retval=", 1)[1].split(" locals=", 1)[0]
    doi = ast.literal_eval(fragment)
    if not isinstance(doi, str):
        raise TypeError(f"Expected str retval, got {type(doi)}")

    return {"doi_char_len": len(doi)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/doi_indirect_full_return_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/doi_indirect_full_return_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "fake = Faker()\n"
        "fake.seed_instance(777777)\n"
        "fake.uuid4()\n"
        "fake.password(length=12)\n"
        "fake.lexify('????')\n"
        "fake.hex_color()\n"
        "fake.doi()\n"
    )

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `faker_qa/doi_indirect_full_return_output/files/testcase.py`, class "
            "`TestDoiIndirectFullReturnOutputQA`, method "
            "`test_doi_indirect_full_return_output_case`. In that test, line 11 constructs `Faker()`, "
            "line 12 calls `seed_instance(777777)`, lines 13-16 call `uuid4()`, `password(length=12)`, "
            "`lexify('????')`, and `hex_color()` to advance the shared generator, and line 17 calls `doi()`. "
            "In `faker/providers/doi/__init__.py::Provider.doi` (lines 10-22), `registrant` is "
            "`str(self.generator.random.randint(1000, 99999999))` (so its string length varies between 4 and 8 "
            "decimal digits) and `suffix` is exactly seven characters from `bothify(\"?#?#?##\").lower()`, "
            "then the method returns `f\"{prefix}.{registrant}/{suffix}\"` with `prefix = \"10\"`. This is a "
            "**Type and Shape** task: what is the exact integer value of `len(s)` where `s` is the **full** "
            "string returned by that `doi()` call (counting every character, including `.` and `/`)?"
        ),
        "template_answer": {
            "doi_char_len": "int",
        },
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
