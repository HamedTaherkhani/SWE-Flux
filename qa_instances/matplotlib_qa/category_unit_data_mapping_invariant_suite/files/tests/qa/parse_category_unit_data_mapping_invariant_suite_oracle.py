#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/lib/matplotlib/category.py"
TARGET_FUNC = "matplotlib.category.UnitData.update"
TARGET_LINE = 221

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) "
)


def _parse_changed_locals(raw_line: str) -> dict[str, object]:
    marker = " locals="
    index = raw_line.find(marker)
    if index < 0:
        return {}
    raw_locals = raw_line[index + len(marker):].strip()
    try:
        parsed = ast.literal_eval(raw_locals)
    except (SyntaxError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}

    decoded: dict[str, object] = {}
    for key, value in parsed.items():
        if isinstance(value, str):
            try:
                decoded[key] = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                decoded[key] = value
        else:
            decoded[key] = value
    return decoded


def extract_invariant(trace_text: str) -> dict[str, bool]:
    # Keep a per-invocation locals snapshot for the target function
    frame_stack: list[dict[str, object]] = []
    seen_any = False
    invariant_holds_for_all = True

    for raw_line in trace_text.splitlines():
        m = EVENT_RE.match(raw_line)
        if not m:
            continue
        if m.group("path") != TARGET_PATH or m.group("func") != TARGET_FUNC:
            continue

        event = m.group("event")
        lineno = int(m.group("lineno"))

        if event == "call":
            frame_stack.append({})
            continue

        if event in {"return", "exception"}:
            if frame_stack:
                frame_stack.pop()
            continue

        if event != "line" or not frame_stack:
            continue

        changed = _parse_changed_locals(raw_line)
        if changed:
            frame_stack[-1].update(changed)

        if lineno != TARGET_LINE:
            continue

        current = frame_stack[-1]
        # At line 221, we should have val and self._mapping
        if "val" not in current or "self" not in current:
            continue
        
        # Extract the mapping from self
        self_obj = current.get("self")
        if not isinstance(self_obj, dict):
            continue
        if "_mapping" not in self_obj:
            continue
        
        mapping = self_obj["_mapping"]
        if not isinstance(mapping, dict):
            continue
        
        val = current["val"]
        
        seen_any = True
        # The invariant: val should NOT be in mapping at line 221 
        # (due to the if condition on line 220)
        invariant = val not in mapping
        if not invariant:
            invariant_holds_for_all = False

    return {"invariant_exists": seen_any and invariant_holds_for_all}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "category_unit_data_mapping_invariant_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "category_unit_data_mapping_invariant_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_invariant(trace_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the full test suite in "
            "`tests/qa/category_unit_data_mapping_invariant_suite_test.py` "
            "(all test cases in class "
            "`TestCategoryUnitDataMappingInvariantSuiteQA`, 24 tests). "
            "Each test creates a `UnitData()` instance and calls `.update(data)`. "
            "Focus on `lib/matplotlib/category.py`, function "
            "`matplotlib.category.UnitData.update`. "
            "At line `221` (`self._mapping[val] = next(self._counter)`), consider "
            "local variables `val` and `self._mapping`. Across all evaluations of this line "
            "over the full suite, is the property "
            "`val not in self._mapping` an invariant property? "
            "Return JSON as `{\\\"invariant_exists\\\": <bool>}` where `true` means the property "
            "holds for every evaluation and `false` means it does not hold."
        ),
        "template_answer": {
            "invariant_exists": "bool"
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
