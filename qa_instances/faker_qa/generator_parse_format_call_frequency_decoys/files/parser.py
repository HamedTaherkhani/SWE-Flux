#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def extract_output(trace_text: str) -> dict[str, int]:
    n = 0
    for line in trace_text.splitlines():
        if "faker.generator.format event=call" not in line:
            continue
        n += 1
    if n == 0:
        raise ValueError("No faker.generator.format call events found in trace log.")
    return {"format_call_count": n}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/generator_parse_format_call_frequency_decoys/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/generator_parse_format_call_frequency_decoys/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "Faker.seed(314159)\n"
        "fake = Faker()\n"
        "fake.set_arguments('rng_lo', {'min_value': 0, 'max_value': 9})\n"
        "fake.set_arguments('rng_hi', {'min_value': 1000, 'max_value': 2000})\n"
        "fake.set_arguments('orphan', {'never': 'used'})\n"
        "fake.set_arguments('decoy', {'x': 1})\n"
        "template = (\n"
        "    '{{ pyint:rng_lo }} {{ pyint:rng_hi }} {{ pyint:rng_lo }} '\n"
        "    '{{ hex_color }} {{ rgb_color }} {{ rgb_css_color }} '\n"
        "    '{{ color_name }} {{ pyint:rng_lo }}'\n"
        ")\n"
        "fake.parse(template)\n"
    )

    qa = {
        "question_kind": "S6_InterProceduralCFG",
        "question": (
            "Use `faker_qa/generator_parse_format_call_frequency_decoys/files/testcase.py`, class "
            "`TestGeneratorParseFormatCallFrequencyDecoysQA`, method "
            "`test_generator_parse_format_call_frequency_decoys_case`. The test seeds with "
            "`Faker.seed(314159)`, registers **four** argument groups via `set_arguments` "
            "(`rng_lo`, `rng_hi`, `orphan`, `decoy`), then calls `fake.parse(template)` where "
            "`template` contains eight `{{ ... }}` tokens mixing `pyint` with named groups and "
            "several color-related formatters (`hex_color`, `rgb_color`, `rgb_css_color`, "
            "`color_name`). "
            "Some registered groups are never referenced by any token (decoys). "
            "Under the runtime semantics of `faker/generator.py` (`parse` → `_re_token.sub` → "
            "`__format_token` → `format`), exactly how many **calls** are made to "
            "`faker.generator.format` (the traced name is `faker.generator.format`, i.e. "
            "`Generator.format`) during that single `parse` invocation?"
        ),
        "template_answer": {"format_call_count": "int"},
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
