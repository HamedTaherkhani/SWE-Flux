#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin records every `event=return` for `random_uuidv4`. We collect
# all 5 retvals, then check whether they are pair-wise identical.
RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.random_uuidv4) "
    r"event=return retval=(?P<retval>.*?) locals=\{.*\}$",
    re.MULTILINE,
)


def extract_outputs(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if len(matches) != 5:
        raise ValueError(
            f"Expected exactly 5 random_uuidv4 return events, got {len(matches)}.")
    retvals = [ast.literal_eval(m.group("retval")) for m in matches]
    return {
        "all_outputs_identical": all(r == retvals[0] for r in retvals),
        "distinct_output_count": len(set(retvals)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/random_uuidv4_output_determinism/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/random_uuidv4_output_determinism/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_outputs(trace_text)

    qa = {
        "question_kind": "determinism_flakiness",
        "question": (
            "Use `test/qa/random_uuidv4_output_determinism_test.py`, class "
            "`TestRandomUuidv4OutputDeterminismQA`, method "
            "`test_random_uuidv4_output_determinism_case`. "
            "The test runs the following block exactly once:\n"
            "```\n"
            "results = []\n"
            "for _ in range(5):\n"
            "    random.seed(42)\n"
            "    results.append(random_uuidv4())\n"
            "```\n"
            "where `random_uuidv4` is `yt_dlp.utils._utils.random_uuidv4` (defined at line "
            "4693), implemented as "
            "`return re.sub(r'[xy]', lambda x: _HEX_TABLE[random.randint(0, 15)], "
            "'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx')`. The function makes 32 calls to "
            "`random.randint(0, 15)` (one for every `x`/`y` placeholder in the template), "
            "drawing from Python's GLOBAL random module state. The test reseeds that "
            "global state with `random.seed(42)` IMMEDIATELY before each call, inside the "
            "for-loop body. "
            "Across the 5 invocations of `random_uuidv4()` performed by this test (one per "
            "loop iteration, in iteration order), are ALL FIVE returned UUIDs equal to "
            "each other (i.e., do all five `event=return` retvals match the first one "
            "byte-for-byte)? "
            "Return a JSON object with two keys: `all_outputs_identical` -- boolean, "
            "`true` if all five retvals are the same string, `false` otherwise -- and "
            "`distinct_output_count` -- int, the number of distinct retvals across the "
            "five calls (`len(set(retvals))`)."
        ),
        "template_answer": {
            "all_outputs_identical": "bool",
            "distinct_output_count": "int",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
