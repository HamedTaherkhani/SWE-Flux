#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Lines look like:
#   .../faker/proxy.py:163 faker.proxy._select_factory event=call locals=...
CALL_RE = re.compile(
    r"/faker/proxy\.py:\d+ (faker\.proxy\.(_select_factory|_map_provider_method|_select_factory_choice|_select_factory_distribution)) event=call"
)


def extract_output(trace_text: str) -> dict[str, list[dict[str, str]]]:
    order: list[dict[str, str]] = []
    for line in trace_text.splitlines():
        m = CALL_RE.search(line.replace("\\", "/"))
        if not m:
            continue
        full = m.group(1)
        order.append({"file": "faker/proxy.py", "func": full})
    if len(order) != 9:
        raise ValueError(
            f"Expected exactly 9 proxy dispatch call events, found {len(order)}.",
        )
    return {"function_call_order": order}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/multilocale_weighted_proxy_dispatch_function_call_order/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/multilocale_weighted_proxy_dispatch_function_call_order/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "Faker.seed(424242)\n"
        "fake = Faker({'en_US': 5, 'de_DE': 15, 'it_IT': 25})\n"
        "fake.first_name()\n"
        "fake.last_name()\n"
        "fake.name()\n"
    )

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `faker_qa/multilocale_weighted_proxy_dispatch_function_call_order/files/testcase.py`, class "
            "`TestMultilocaleWeightedProxyDispatchFunctionCallOrderQA`, method "
            "`test_multilocale_weighted_proxy_dispatch_function_call_order_case`. "
            "The test runs `Faker.seed(424242)`, builds a **weighted** multi-locale proxy "
            "`Faker({'en_US': 5, 'de_DE': 15, 'it_IT': 25})`, then invokes `first_name()`, "
            "`last_name()`, and `name()` on that proxy. "
            "Restrict attention to **call** events in file `faker/proxy.py` and **only** these "
            "functions: `faker.proxy._select_factory`, `faker.proxy._map_provider_method`, "
            "`faker.proxy._select_factory_choice`, and `faker.proxy._select_factory_distribution`. "
            "What is the exact ordered sequence of these function calls (including repeats), "
            "as a list of objects with keys `file` and `func`?"
        ),
        "template_answer": {
            "function_call_order": [{"file": "str", "func": "str"}],
        },
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
