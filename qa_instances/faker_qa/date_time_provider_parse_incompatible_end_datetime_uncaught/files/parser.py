#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

PARSE_DT_EXC_RE = re.compile(
    r"faker\.providers\.date_time\._parse_date_time event=exception "
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
        m = PARSE_DT_EXC_RE.search(line)
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
    raise ValueError("Could not find _parse_date_time exception event in trace log.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/date_time_provider_parse_incompatible_end_datetime_uncaught/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/date_time_provider_parse_incompatible_end_datetime_uncaught/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "fake = Faker()\n"
        "fake.seed_instance(1729)\n"
        "fake.date_time_this_decade(before_now=True, after_now=False)\n"
        "fake.past_datetime(\"-10d\")\n"
        "fake.date_time_between(start_date=\"-2h\", "
        "end_date={\"tz\": \"invalid\", \"nested\": [1, 2, 3]})\n"
    )

    qa = {
        "question_kind": "S6_Exceptions",
        "question": (
            "Use `faker_qa/date_time_provider_parse_incompatible_end_datetime_uncaught/files/testcase.py`, class "
            "`TestDateTimeProviderParseIncompatibleEndDatetimeUncaughtQA`, method "
            "`test_date_time_provider_parse_incompatible_end_datetime_uncaught_case`. After `seed_instance(1729)`, "
            "`date_time_this_decade` constrains sampling to the current decade relative to `datetime.now`, and "
            "`past_datetime` composes `date_time_between` with parsed timedelta endpoints. The final "
            "`date_time_between` passes a negative timedelta string for `start_date` but a plain Python `dict` for "
            "`end_date`. That flows into `Provider._parse_date_time` in `faker/providers/date_time/__init__.py`, "
            "which accepts datetimes, `timedelta`, `str` tokens (`now`, timedelta strings), or `int` timestamps — but "
            "not arbitrary mappings. What exact exception type and exception message are thrown as an uncaught "
            "exception from that `_parse_date_time` call (i.e., the exception that propagates out of the date_time "
            "provider and is caught by the test harness)?"
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
