#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

COMPANY_SUFFIX_EXC_RE = re.compile(
    r"faker\.providers\.company\.company_suffix event=exception exc=(?P<exc_name>\w+): (?P<repr_rest>.+?) locals=",
)


def _message_from_repr_exception(repr_rest: str) -> tuple[str, str]:
    repr_rest = repr_rest.strip()
    m = re.match(r"^(\w+)\((.*)\)$", repr_rest, re.DOTALL)
    if not m:
        raise ValueError(f"Unexpected exception repr in trace: {repr_rest!r}")
    inner = m.group(2)
    message = ast.literal_eval(inner)
    return m.group(1), message


def extract_output(trace_text: str) -> dict[str, str]:
    for line in trace_text.splitlines():
        m = COMPANY_SUFFIX_EXC_RE.search(line)
        if not m:
            continue
        exc_name = m.group("exc_name")
        repr_rest = m.group("repr_rest")
        inner_type, message = _message_from_repr_exception(repr_rest)
        if inner_type != exc_name:
            raise ValueError(
                f"Mismatched exception names in trace line: {exc_name!r} vs {inner_type!r}",
            )
        return {
            "exception_type": exc_name,
            "exception_message": message,
        }
    raise ValueError("Could not find company_suffix() exception event in trace log.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/company_provider_empty_suffixes_indexerror_uncaught/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/company_provider_empty_suffixes_indexerror_uncaught/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "fake = Faker()\n"
        "fake.seed_instance(1618)\n"
        "fake.company()\n"
        "fake.catch_phrase()\n"
        "fake.company_suffix()\n"
        "company_provider = fake.provider(\"faker.providers.company\")\n"
        "company_provider.company_suffixes = ()\n"
        "fake.company_suffix()\n"
    )

    qa = {
        "question_kind": "S5_Exceptions",
        "question": (
            "Use `faker_qa/company_provider_empty_suffixes_indexerror_uncaught/files/testcase.py`, class "
            "`TestCompanyProviderEmptySuffixesIndexErrorUncaughtQA`, method "
            "`test_company_provider_empty_suffixes_indexerror_uncaught_case`. After `seed_instance(1618)`, the "
            "test calls `company()` (which parses a `formats` template through `generator.parse`), `catch_phrase` "
            "(which samples from each tuple in `catch_phrase_words`), and a successful `company_suffix()`. It then "
            "resolves `faker.providers.company` via `Generator.provider` and assigns `company_suffixes` to an empty "
            "tuple. The final `fake.company_suffix()` enters `faker/providers/company/__init__.py::Provider."
            "company_suffix` (lines 515–519), which returns `self.random_element(self.company_suffixes)` on an "
            "empty sequence. What exact exception type and exception message are thrown as an uncaught exception "
            "from that `company_suffix` invocation (i.e., the exception that propagates out of the company provider "
            "and is caught by the test harness)?"
        ),
        "template_answer": {
            "exception_type": "str",
            "exception_message": "str",
        },
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
