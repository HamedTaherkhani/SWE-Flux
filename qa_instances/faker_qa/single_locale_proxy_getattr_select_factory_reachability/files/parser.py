#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Real calls to these functions (not `__getattribute__` lookups by name).
GETATTR_CALL = re.compile(
    r"/faker/proxy\.py:\d+ faker\.proxy\.__getattr__ event=call"
)
SELECT_FACTORY_CALL = re.compile(
    r"/faker/proxy\.py:\d+ faker\.proxy\._select_factory event=call"
)


def extract_output(trace_text: str) -> dict[str, bool]:
    text = trace_text.replace("\\", "/")
    getattr_invoked = bool(GETATTR_CALL.search(text))
    select_factory_invoked = bool(SELECT_FACTORY_CALL.search(text))
    return {
        "proxy_getattr_invoked": getattr_invoked,
        "proxy_select_factory_invoked": select_factory_invoked,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/single_locale_proxy_getattr_select_factory_reachability/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/single_locale_proxy_getattr_select_factory_reachability/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "Faker.seed(999)\n"
        "fake = Faker()\n"
        "fake.first_name()\n"
    )

    qa = {
        "question_kind": "S2_InterProceduralCFG",
        "question": (
            "Use `faker_qa/single_locale_proxy_getattr_select_factory_reachability/files/testcase.py`, class "
            "`TestSingleLocaleProxyGetattrSelectFactoryReachabilityQA`, method "
            "`test_single_locale_proxy_getattr_select_factory_reachability_case`. "
            "The test runs `Faker.seed(999)`, constructs a **default single-locale** `Faker()`, "
            "then calls `fake.first_name()`. "
            "Considering **only** traced `call` events in `faker/proxy.py` during that test: "
            "(1) Is `faker.proxy.__getattr__` ever invoked? "
            "(2) Is `faker.proxy._select_factory` ever invoked (a real `call` to the function body, "
            "not merely `__getattribute__` retrieving the name `'_select_factory'` as a string)? "
            "Answer with booleans `proxy_getattr_invoked` and `proxy_select_factory_invoked`."
        ),
        "template_answer": {
            "proxy_getattr_invoked": "bool",
            "proxy_select_factory_invoked": "bool",
        },
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
