#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

# Trace log line (trace_plugin): exception repr uses exc_type.__name__ + ": " + repr(exc_val)
PYFLOAT_EXC_RE = re.compile(
    r"faker\.providers\.python\.pyfloat event=exception exc=(?P<exc_name>\w+): (?P<repr_rest>.+?) locals=",
)


def _message_from_repr_exception(repr_rest: str) -> tuple[str, str]:
    """
    repr_rest is repr(e), e.g. TypeError("'>' not supported between instances of 'list' and 'int'").
    Returns (exception type name, message string str(e)).
    """
    repr_rest = repr_rest.strip()
    m = re.match(r"^(\w+)\((.*)\)$", repr_rest, re.DOTALL)
    if not m:
        raise ValueError(f"Unexpected exception repr in trace: {repr_rest!r}")
    inner = m.group(2)
    message = ast.literal_eval(inner)
    return m.group(1), message


def extract_output(trace_text: str) -> dict[str, str]:
    for line in trace_text.splitlines():
        m = PYFLOAT_EXC_RE.search(line)
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
    raise ValueError("Could not find pyfloat exception event in trace log.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/python_provider_pyfloat_incompatible_compare_uncaught/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/python_provider_pyfloat_incompatible_compare_uncaught/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "fake = Faker()\n"
        "fake.seed_instance(271828)\n"
        "fake.pylist(nb_elements=14, variable_nb_elements=True, "
        "value_types=(\"str\", \"int\", \"float\", \"decimal\", \"tuple\"), "
        "allowed_types=(\"date_time\",))\n"
        "fake.pyset(nb_elements=3, variable_nb_elements=False, value_types=(\"str\",))\n"
        "fake.pyfloat(min_value=[0, 1], max_value=100)\n"
    )

    qa = {
        "question_kind": "S5_Exceptions",
        "question": (
            "Use `faker_qa/python_provider_pyfloat_incompatible_compare_uncaught/files/testcase.py`, class "
            "`TestPythonProviderPyfloatIncompatibleCompareUncaughtQA`, method "
            "`test_python_provider_pyfloat_incompatible_compare_uncaught_case`. After `seed_instance(271828)`, "
            "the call to `pylist` (lines assigning the container) flows through `_check_signature`, `_pyiterable`, "
            "`_random_type`, and `generator.format` for each element while `allowed_types` adds `date_time` to the "
            "merged signature. The `pyset` call reuses the same iterable machinery with a fixed element count. "
            "The final `pyfloat` call passes a list `min_value` and an int `max_value`, so the guard at "
            "`faker/providers/python/__init__.py::Provider.pyfloat` lines 157–158 evaluates `min_value > max_value` "
            "before any numeric coercion. What exact exception type and exception message are thrown as an uncaught "
            "exception from that `pyfloat` invocation (i.e., the exception that propagates out of the python "
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
