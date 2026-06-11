#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

def extract_weights(trace_text: str) -> list[int]:
    for line in trace_text.splitlines():
        if "proxy.py:173" not in line.replace("\\", "/"):
            continue
        if "faker.proxy._select_factory" not in line:
            continue
        m = re.search(r"'weights':\s*'(\[[^\]]*\])'", line)
        if not m:
            continue
        val = ast.literal_eval(m.group(1))
        if not isinstance(val, list):
            raise ValueError(f"Expected list for weights, got {type(val)}")
        return [int(x) for x in val]
    raise ValueError(
        "Could not find `weights` locals on proxy.py:173 for `_select_factory` in the trace.",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/weighted_proxy_select_factory_if_weights_snapshot/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/weighted_proxy_select_factory_if_weights_snapshot/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    weights = extract_weights(trace_text)

    execution = (
        "from faker import Faker\n"
        "Faker.seed(4242)\n"
        "fake = Faker({'en_US': 1, 'de_DE': 4, 'ja_JP': 9})\n"
        "fake.word()\n"
    )

    qa = {
        "question_kind": "S3_ProgramState",
        "question_subtype": "condition_variable_snapshot",
        "question": (
            "Use `faker_qa/weighted_proxy_select_factory_if_weights_snapshot/files/testcase.py`, class "
            "`TestWeightedProxySelectFactoryIfWeightsSnapshotQA`, method "
            "`test_weighted_proxy_select_factory_if_weights_snapshot_case`. The test seeds the shared "
            "Faker RNG with `Faker.seed(4242)`, constructs a **weighted** three-locale proxy "
            "`Faker({'en_US': 1, 'de_DE': 4, 'ja_JP': 9})`, then calls `fake.word()`. That call is "
            "resolved through `faker/proxy.py`: `Faker.__getattr__` dispatches to `_select_factory` "
            "because multiple underlying factories exist. Inside `faker.proxy.Faker._select_factory`, "
            "after `factories, weights = self._map_provider_method(method_name)` (line `171`), control "
            "passes the `len(factories)` guards (lines `173`–`177`). "
            "At the **exact moment** the `if` condition on **line `179`** "
            "(`if weights:`) is evaluated for this `word` resolution, what is the **exact** value of "
            "the variable `weights` (the object whose truthiness is tested)? "
            "Return a JSON object with key `weights_snapshot` whose value is a JSON array of integers "
            "in list order (e.g. `[1, 4, 9]`)."
        ),
        "template_answer": {"weights_snapshot": "list[int]"},
        "oracle_answer": {"weights_snapshot": weights},
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
