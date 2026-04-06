#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

# After `_check_signature` + filtering, pydict's `_pyiterable` uses this type name list.
_TARGET_TYPE_LIST_REPR = "['int', 'str', 'float']"


def _parse_retval(retval_raw: str):
    s = retval_raw.strip()
    if not s:
        raise ValueError("Empty retval fragment in trace line.")
    try:
        return ast.literal_eval(s)
    except (SyntaxError, ValueError):
        raise ValueError(f"Could not parse retval with literal_eval: {s!r}")


def extract_output(trace_text: str) -> dict[str, list[object]]:
    sequence: list[object] = []
    for line in trace_text.splitlines():
        if "faker.providers.python._random_type" not in line:
            continue
        if " event=return " not in line:
            continue
        if _TARGET_TYPE_LIST_REPR not in line:
            continue
        if " retval=" not in line or " locals=" not in line:
            continue
        pre, _loc = line.rsplit(" locals=", 1)
        if "event=return retval=" not in pre:
            continue
        retval_raw = pre.split("event=return retval=", 1)[1]
        sequence.append(_parse_retval(retval_raw))

    if not sequence:
        raise ValueError(
            "Could not find _random_type return events for pydict (type_list "
            f"containing {_TARGET_TYPE_LIST_REPR!r}).",
        )

    return {"pydict_random_type_return_sequence": sequence}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/python_provider_pydict_indirect_random_type_seq/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/python_provider_pydict_indirect_random_type_seq/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "fake = Faker()\n"
        "fake.seed_instance(424242)\n"
        "fake.pystruct(count=3, value_types=(str, int, float))\n"
        "fake.pydict(\n"
        "    nb_elements=4,\n"
        "    variable_nb_elements=True,\n"
        "    value_types=(int, str),\n"
        "    allowed_types=(float,),\n"
        ")\n"
    )

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `faker_qa/python_provider_pydict_indirect_random_type_seq/files/testcase.py`, class "
            "`TestPythonProviderPydictIndirectRandomTypeSeqQA`, method "
            "`test_python_provider_pydict_indirect_random_type_seq_case`. In that test, line 13 calls "
            "`seed_instance(424242)`, lines 14-17 call `pystruct(count=3, value_types=(str, int, float))`, "
            "and lines 18-23 call `pydict(nb_elements=4, variable_nb_elements=True, value_types=(int, str), "
            "allowed_types=(float,))`. The `pystruct` phase walks nested dict/tuple scaffolding and repeatedly "
            "invokes `_random_type` while the merged RNG stream advances. The subsequent `pydict` call pairs "
            "`generator.words(nb_elements, unique=True)` with `_pyiterable`, which yields four values via "
            "`_random_type` after `_check_signature` produces a normalized type name list. During this "
            "indirect execution limited to `faker/providers/python/__init__.py::Provider._random_type`, what "
            "is the exact ordered sequence of **return values** from `_random_type` for those four "
            "`pydict` value draws (i.e., the returns where `type_list` is `['int', 'str', 'float']` in the "
            "traced locals)?"
        ),
        "template_answer": {
            "pydict_random_type_return_sequence": [
                "float | int | str",
                "float | int | str",
                "float | int | str",
                "float | int | str",
            ]
        },
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
