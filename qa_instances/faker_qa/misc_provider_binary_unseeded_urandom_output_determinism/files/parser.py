#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH_SUBSTR = "faker/providers/misc/__init__.py"
TARGET_FUNCS = {
    "faker.providers.misc.binary",
    "faker.providers.misc.Provider.binary",
}

# Return lines look like:
# .../misc/__init__.py:61 faker.providers.misc.binary event=return retval=b'...' locals={...}
RETURN_RE = re.compile(
    r"(?P<path>/testbed/faker/providers/misc/__init__\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=return retval=(?P<retval>.+?) locals=\{"
)


def extract_binary_retvals(trace_text: str) -> list[str]:
    out: list[str] = []
    for raw_line in trace_text.splitlines():
        m = RETURN_RE.match(raw_line)
        if not m:
            continue
        if TARGET_PATH_SUBSTR not in m.group("path").replace("\\", "/"):
            continue
        if m.group("func") not in TARGET_FUNCS:
            continue
        out.append(m.group("retval"))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/faker_qa/misc_provider_binary_unseeded_urandom_output_determinism/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/faker_qa/misc_provider_binary_unseeded_urandom_output_determinism/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    retvals = extract_binary_retvals(trace_text)

    invariant_exists = len(retvals) == 10 and len(set(retvals)) == 1

    execution = (
        "from faker import Faker\n"
        "fake = Faker()\n"
        "fake.binary(48)\n"
    )

    qa = {
        "question_kind": "M3_ProgramState",
        "question": (
            "Execute "
            "`faker_qa/misc_provider_binary_unseeded_urandom_output_determinism/files/testcase.py::"
            "TestMiscProviderBinaryUrandomOutputDeterminismQA::"
            "test_misc_provider_binary_unseeded_urandom_output_determinism_case` exactly 10 "
            "independent times with identical inputs. The test constructs `Faker()` and **does not** "
            "call `Faker.seed` or `seed_instance`. It invokes `binary(48)` once. "
            "In `faker/providers/misc/__init__.py`, `Provider.binary` branches on "
            "`self.generator._is_seeded`: when false, it returns `os.urandom(length)` (line 61); "
            "when true, it builds bytes from `random.randrange(256)` in a list comprehension "
            "(lines 56–58). Given this unseeded configuration, is the **returned value** of `binary` "
            "identical on every one of the 10 runs? Return JSON with exactly one key: "
            "`{\"invariant_exists\": <bool>}` — `true` only if all 10 returned `bytes` values are equal, "
            "`false` otherwise."
        ),
        "template_answer": {
            "invariant_exists": "bool",
        },
        "oracle_answer": {
            "invariant_exists": invariant_exists,
        },
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
