#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/lib/matplotlib/colors.py"
TARGET_LINE = 388
TARGET_FUNC = "matplotlib.colors._to_rgba_no_colorcycle"
EXPECTED_C_STR = "0.371825413792"

LINE388_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    rf"(?P<path>{re.escape(TARGET_PATH)}):{TARGET_LINE} "
    rf"{re.escape(TARGET_FUNC)} event=line locals=(?P<locals>\{{.*\}})\s*$"
)

# locals values are trace_plugin _safe_repr strings; c is emitted as '0.3718...'
C_IN_LOCALS_RE = re.compile(r"'c':\s*'([0-9.eE+-]+)'")


def _parse_c_from_locals_blob(blob: str) -> float | None:
    m = C_IN_LOCALS_RE.search(blob)
    if not m:
        return None
    return float(m.group(1))


def extract_condition_snapshot(trace_text: str) -> dict:
    hits: list[float] = []
    for raw in trace_text.splitlines():
        m = LINE388_RE.match(raw)
        if not m or m.group("path") != TARGET_PATH:
            continue
        c_val = _parse_c_from_locals_blob(m.group("locals"))
        if c_val is None:
            continue
        if abs(c_val - float(EXPECTED_C_STR)) < 1e-12:
            hits.append(c_val)
    if not hits:
        raise ValueError(
            "Could not find line 388 condition snapshot for the target grayscale literal."
        )
    # Every test must use the same literal so all hits agree on one oracle.
    rounded = [round(h, 15) for h in hits]
    if len(set(rounded)) != 1:
        raise ValueError(
            f"Inconsistent c at line 388 across runs: {hits!r} "
            "(all tests must use the same grayscale literal)."
        )
    c = hits[-1]
    interval_ok = 0 <= c <= 1
    return {"condition_values": [c, interval_ok]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/colors_nocolorcycle_grayscale_interval_condition_snapshot/"
            "trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/colors_nocolorcycle_grayscale_interval_condition_snapshot/"
            "oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    oracle_answer = extract_condition_snapshot(trace_text)

    qa = {
        "question_kind": "conditional_statements",
        "question": (
            "Use `tests/qa/colors_nocolorcycle_grayscale_interval_condition_snapshot_test.py`, class "
            "`TestColorsNocolorcycleGrayscaleIntervalConditionSnapshotQA` (all of its test methods). "
            "The module loads the project `matplotlib.colors` implementation from `lib/` via "
            "`importlib.import_module` after inserting the repository `lib` directory on "
            "`sys.path` (it does not use a top-level `import matplotlib` statement). "
            "Each test calls `_to_rgba_no_colorcycle` with the same string grayscale literal "
            f"`'{EXPECTED_C_STR}'` and `alpha=None` (possibly via helpers, `getattr`, or other "
            "indirection). "
            "In `lib/matplotlib/colors.py`, at the exact moment the condition on line 388 inside "
            "`matplotlib.colors._to_rgba_no_colorcycle` is evaluated "
            "(`if not (0 <= c <= 1):`, immediately after `c = float(c)` in the `try`/`else` "
            "path for string colors), what are the exact values of `c` (as a float) and of the "
            "subexpression `(0 <= c <= 1)` before the `not` is applied? "
            "Return JSON with exactly one key `condition_values` whose value is a two-element "
            "list `[c, (0 <= c <= 1)]` using a JSON boolean for the second element."
        ),
        "template_answer": {
            "condition_values": ["float", "bool"],
        },
        "oracle_answer": oracle_answer,
        "execution": {
            "eval_entry": (
                "matplotlib_qa/colors_nocolorcycle_grayscale_interval_condition_snapshot/eval.sh"
            ),
            "trace_policy": {
                "trace_file_substr": "lib/matplotlib/colors.py",
                "trace_func": "matplotlib.colors._to_rgba_no_colorcycle",
                "notes": (
                    "Line-level trace at colors.py:388; locate the invocation tied to the unique "
                    "grayscale string; read traced local `c` and derive `(0 <= c <= 1)`."
                ),
            },
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
