#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_PATH = "/testbed/sympy/stats/stochastic_process_types.py"
TARGET_FUNC = "sympy.stats.stochastic_process_types.DiscreteMarkovChain.communication_classes"
TARGET_LINE = 1073

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/sympy/stats/[^:]+):(?P<lineno>\d+) "
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
    relation_holds_for_all = True

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
        if "current_level" not in current or "i" not in current or "level" not in current:
            continue
        if not isinstance(current["current_level"], int):
            continue
        if not isinstance(current["i"], int):
            continue
        if not isinstance(current["level"], dict):
            continue
        if current["i"] not in current["level"]:
            continue
        if not isinstance(current["level"][current["i"]], int):
            continue

        seen_any = True
        relation = current["current_level"] == current["level"][current["i"]] + 1
        if not relation:
            relation_holds_for_all = False

    return {"invariant_exists": seen_any and relation_holds_for_all}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=(
            "/testbed/logs/qa_instances/"
            "stats_markov_canonical_level_relation_invariant_suite/trace.log"
        ),
    )
    parser.add_argument(
        "--out",
        default=(
            "/testbed/logs/qa_instances/"
            "stats_markov_canonical_level_relation_invariant_suite/oracle.json"
        ),
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_invariant(trace_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the full test suite in "
            "`tests/qa/stats_markov_canonical_level_relation_invariant_suite_test.py` "
            "(all generated test cases in class "
            "`TestStatsMarkovCanonicalLevelRelationInvariantSuiteQA`, 24 tests). "
            "Each test calls `DiscreteMarkovChain(...).canonical_form()`, which calls "
            "`sympy.stats.stochastic_process_types.DiscreteMarkovChain.decompose` and then "
            "`sympy.stats.stochastic_process_types.DiscreteMarkovChain.communication_classes`. "
            "In file `sympy/stats/stochastic_process_types.py`, function "
            "`sympy.stats.stochastic_process_types.DiscreteMarkovChain.communication_classes`, "
            "at line `1073` (`newly_visited = {j for j in class_ if T[i, j] != 0}`), consider "
            "local variables `current_level` and `level[i]`. Across all evaluations of this line "
            "over the full suite, is the relationship "
            "`current_level == level[i] + 1` an invariant property? "
            "Return JSON as `{\\\"invariant_exists\\\": <bool>}` where `true` means invariant "
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
