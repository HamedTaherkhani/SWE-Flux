#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


def extract_output(trace_text: str) -> dict[str, str]:
    lines = []
    for line in trace_text.splitlines():
        if "faker.providers.currency.pricetag" not in line:
            continue
        if " event=return " not in line:
            continue
        lines.append(line)

    if not lines:
        raise ValueError("Could not find pricetag return events in trace log.")

    target_line = lines[-1]
    if "event=return retval=" not in target_line or " locals=" not in target_line:
        raise ValueError(f"Unexpected pricetag return line format: {target_line!r}")

    fragment = target_line.split("event=return retval=", 1)[1].split(" locals=", 1)[0]
    pricetag = ast.literal_eval(fragment)
    if not isinstance(pricetag, str):
        raise TypeError(f"Expected str retval, got {type(pricetag)}")

    return {"pricetag": pricetag}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/currency_th_th_pricetag_indirect_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/currency_th_th_pricetag_indirect_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "fake = Faker('th_TH')\n"
        "fake.seed_instance(314159)\n"
        "fake.cryptocurrency()\n"
        "fake.cryptocurrency_name()\n"
        "fake.currency_name()\n"
        "fake.currency_symbol()\n"
        "fake.pricetag()\n"
    )

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `faker_qa/currency_th_th_pricetag_indirect_output/files/testcase.py`, class "
            "`TestCurrencyThThPricetagIndirectOutputQA`, method "
            "`test_currency_th_th_pricetag_indirect_output_case`. In that test, line 11 constructs "
            "`Faker('th_TH')`, line 12 calls `seed_instance(314159)`, lines 13-16 call `cryptocurrency()`, "
            "`cryptocurrency_name()`, `currency_name()`, and `currency_symbol()` (each exercising "
            "different tuple or dict pools on the currency provider), and line 17 calls `pricetag()`. "
            "Unlike `en_US`, the Thai locale does not override `pricetag`, so execution uses the base "
            "implementation in `faker/providers/currency/__init__.py` (lines 423-425): a fiat pair from "
            "`random_element(self.currencies)`, concatenation with a no-break space (`\\N{NO-BREAK SPACE}`), "
            "and `numerify(self.random_element(self.price_formats))`. This is a **Function/Method Output** "
            "task: what is the **exact** string returned by that `pricetag()` call (including the no-break "
            "space between the ISO currency code and the formatted amount)?"
        ),
        "template_answer": {
            "pricetag": "str",
        },
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
