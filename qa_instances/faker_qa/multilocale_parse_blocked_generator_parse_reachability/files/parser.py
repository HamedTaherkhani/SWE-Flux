#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# `__getattr__` resolving `parse` on a multi-locale proxy (attr visible in locals).
PROXY_GETATTR_PARSE = re.compile(
    r"/faker/proxy\.py:\d+ faker\.proxy\.__getattr__ event=call .*'parse'"
)
# Actual body invocation of `Generator.parse` (not `set_formatter` / other generator APIs).
GENERATOR_PARSE_CALL = re.compile(
    r"/faker/generator\.py:\d+ faker\.generator\.parse event=call"
)


def extract_output(trace_text: str) -> dict[str, bool]:
    text = trace_text.replace("\\", "/")
    return {
        "faker_proxy_getattr_parse_reached": bool(PROXY_GETATTR_PARSE.search(text)),
        "faker_generator_parse_reached": bool(GENERATOR_PARSE_CALL.search(text)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/multilocale_parse_blocked_generator_parse_reachability/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/multilocale_parse_blocked_generator_parse_reachability/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "Faker.seed(777)\n"
        "fake = Faker(['fr_FR', 'ja_JP'])\n"
        "try:\n"
        "    fake.parse('{{ name }}')\n"
        "except NotImplementedError:\n"
        "    pass\n"
    )

    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "question": (
            "Use `faker_qa/multilocale_parse_blocked_generator_parse_reachability/files/testcase.py`, class "
            "`TestMultilocaleParseBlockedGeneratorParseReachabilityQA`, method "
            "`test_multilocale_parse_blocked_generator_parse_reachability_case`. "
            "The test seeds with `Faker.seed(777)`, builds a **two-locale** `Faker(['fr_FR', 'ja_JP'])`, "
            "then calls `fake.parse('{{ name }}')` inside `try`/`except NotImplementedError` (the call "
            "is expected to fail at the proxy layer). "
            "Answer these reachability questions using **only** traced `call` events under `/testbed/faker/`: "
            "(1) Does execution reach a **call** to `faker.proxy.__getattr__` where the attribute being "
            "resolved is `parse` (you may rely on trace locals showing `attr` is `'parse'`)? "
            "(2) Does execution reach a **call** to the `parse` **method body** on the generator, i.e. "
            "`faker.generator.parse` (traced name `faker.generator.parse` in `faker/generator.py`)? "
            "Return booleans `faker_proxy_getattr_parse_reached` and `faker_generator_parse_reached`."
        ),
        "template_answer": {
            "faker_proxy_getattr_parse_reached": "bool",
            "faker_generator_parse_reached": "bool",
        },
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
