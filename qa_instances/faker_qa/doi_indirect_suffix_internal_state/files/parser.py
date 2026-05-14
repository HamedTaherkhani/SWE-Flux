#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

_SUFFIX_MARKER = "'suffix': \"'"
_SUFFIX_END = "'\""


def extract_output(trace_text: str) -> dict[str, str]:
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
    idx = target_line.find(_SUFFIX_MARKER)
    if idx < 0:
        raise ValueError(f"Could not find suffix marker in trace line: {target_line!r}")
    start = idx + len(_SUFFIX_MARKER)
    end = target_line.find(_SUFFIX_END, start)
    if end < 0:
        raise ValueError(f"Could not find suffix terminator in trace line: {target_line!r}")

    return {"suffix": target_line[start:end]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/doi_indirect_suffix_internal_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/doi_indirect_suffix_internal_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "fake = Faker()\n"
        "fake.seed_instance(135792468)\n"
        "fake.ean13()\n"
        "fake.word()\n"
        "fake.random_digit()\n"
        "fake.doi()\n"
    )

    qa = {
        "question_kind": "C4_ProgramState",
        "question": (
            "Use `faker_qa/doi_indirect_suffix_internal_state/files/testcase.py`, class "
            "`TestDoiIndirectSuffixInternalStateQA`, method "
            "`test_doi_indirect_suffix_internal_state_case`. In that test, line 11 constructs `Faker()`, "
            "line 12 calls `seed_instance(135792468)`, lines 13-15 call `ean13()`, `word()`, and "
            "`random_digit()`, and line 16 calls `doi()`. In `faker/providers/doi/__init__.py::Provider.doi` "
            "(lines 10-22), after `registrant = str(self.generator.random.randint(1000, 99999999))`, the code "
            "assigns `suffix = self.generator.bothify(\"?#?#?##\").lower()` and returns "
            "`f\"{prefix}.{registrant}/{suffix}\"` with `prefix = \"10\"`. This is a **Variable State "
            "(Internal)** task: at the traced `return` for that `doi()` invocation, what is the **exact** "
            "string value of the local variable `suffix` (the lowercased `bothify` result **before** it is "
            "interpolated into the final DOI string)?"
        ),
        "template_answer": {
            "suffix": "str",
        },
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
