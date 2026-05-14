#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

CC_PROVIDER_EXC_RE = re.compile(
    r"faker\.providers\.credit_card\.credit_card_provider event=exception "
    r"exc=(?P<exc_name>\w+): (?P<repr_rest>.+?) locals=",
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
        m = CC_PROVIDER_EXC_RE.search(line)
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
    raise ValueError("Could not find credit_card_provider() exception event in trace log.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/credit_card_provider_empty_types_indexerror_uncaught/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/credit_card_provider_empty_types_indexerror_uncaught/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from collections import OrderedDict\n"
        "from faker import Faker\n"
        "fake = Faker()\n"
        "fake.seed_instance(2357)\n"
        "fake.credit_card_number()\n"
        "fake.credit_card_expire()\n"
        "fake.credit_card_security_code()\n"
        "cc_provider = fake.provider(\"faker.providers.credit_card\")\n"
        "cc_provider.credit_card_types = OrderedDict()\n"
        "fake.credit_card_provider()\n"
    )

    qa = {
        "question_kind": "C6_Exceptions",
        "question": (
            "Use `faker_qa/credit_card_provider_empty_types_indexerror_uncaught/files/testcase.py`, class "
            "`TestCreditCardProviderEmptyTypesIndexErrorUncaughtQA`, method "
            "`test_credit_card_provider_empty_types_indexerror_uncaught_case`. After `seed_instance(2357)`, the "
            "test calls `credit_card_number` (Luhn construction via `_generate_number`), `credit_card_expire` "
            "(date range parsing), and `credit_card_security_code` (numeric pattern from the selected card type). "
            "It then resolves `faker.providers.credit_card` via `Generator.provider` and replaces "
            "`credit_card_types` with an empty `OrderedDict`, removing every `CardType` entry. The final "
            "`fake.credit_card_provider()` enters `faker/providers/credit_card/__init__.py::Provider.credit_card_"
            "provider` with `card_type is None`, so execution reaches `self.random_element(self.credit_card_types."
            "keys())` (lines 114–115) over an empty key set. What exact exception type and exception message are "
            "thrown as an uncaught exception from that `credit_card_provider` invocation (i.e., the exception that "
            "propagates out of the credit_card provider and is caught by the test harness)?"
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
