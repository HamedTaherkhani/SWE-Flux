#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin records every line event for `_sanitize_path_parts`. Locals
# are emitted as DIFFS (only changed bindings since the previous trace event
# in the same frame). The function body is:
#     682: def _sanitize_path_parts(parts):
#     683:     sanitized_parts = []
#     684:     for part in parts:                                  # for-loop check
#     685:         if not part or part == '.':
#     686:             continue
#     687:         elif part == '..':
#     688:             if sanitized_parts and sanitized_parts[-1] != '..':
#     689:                 sanitized_parts.pop()
#     690:             else:
#     691:                 sanitized_parts.append('..')
#     692:             continue
#     696:         sanitized_part = re.sub(r'[/<>:"\|\\?\*]|[\s.]$', '#', part)
#     697:         sanitized_parts.append(sanitized_part)
#     699:     return sanitized_parts
#
# Empirically (Python 3.9), line 684 (the `for part in parts:` line) fires M+1
# times for M iterations: once at the start of each iteration AND once more at
# the iterator-exhaustion check. So at every line-684 event AFTER the first
# one, the cumulative locals reflect the POST-PREV-ITER state of
# `sanitized_parts`. That gives exactly M post-iter snapshots per call.
EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\._sanitize_path_parts) "
    r"event=(?P<event>line|call|return|exception) ",
    re.MULTILINE,
)

LINE_LOCALS_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\._sanitize_path_parts) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

LOOP_LINE = "684"


def collect_post_iter_states(trace_text: str) -> list[list[str]]:
    locals_lookup = {
        m.start(): ast.literal_eval(m.group("locals"))
        for m in LINE_LOCALS_RE.finditer(trace_text)
    }

    cumulative: dict[str, str] = {}
    in_call = False
    line_684_count = 0
    states: list[list[str]] = []

    for m in EVENT_RE.finditer(trace_text):
        ev = m.group("event")
        ln = m.group("lineno")
        if ev == "call":
            cumulative = {}
            line_684_count = 0
            in_call = True
            continue
        if ev == "return":
            in_call = False
            continue
        if ev == "exception":
            continue
        if ev == "line" and in_call:
            delta = locals_lookup.get(m.start())
            if delta is not None:
                cumulative.update(delta)
            if ln == LOOP_LINE:
                line_684_count += 1
                if line_684_count > 1:
                    if "sanitized_parts" not in cumulative:
                        raise ValueError(
                            f"At line-{LOOP_LINE} (post-iter snapshot) "
                            f"`sanitized_parts` not in cumulative locals: {cumulative!r}")
                    state = ast.literal_eval(cumulative["sanitized_parts"])
                    if not isinstance(state, list):
                        raise ValueError(
                            f"`sanitized_parts` is not a list: {state!r}")
                    states.append(list(state))

    return states


def evaluate(states: list[list[str]]) -> dict:
    violations = 0
    for state in states:
        if any(isinstance(p, str) and p.endswith(".") for p in state):
            violations += 1
    return {
        "total_iterations_observed": len(states),
        "violating_iteration_count": violations,
        "is_invariant_always_held": violations == 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/sanitize_path_parts_loop_value_invariant_suite/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/sanitize_path_parts_loop_value_invariant_suite/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    states = collect_post_iter_states(trace_text)
    output = evaluate(states)

    qa = {
        "question_kind": "M7_Invariants",
        "question": (
            "Use the FULL test suite in "
            "`test/qa/sanitize_path_parts_loop_value_invariant_suite_test.py` (all 18 "
            "test methods in class `TestSanitizePathPartsLoopValueInvariantSuiteQA`). "
            "Each test method calls "
            "`yt_dlp.utils._utils._sanitize_path_parts(<list_of_strings>)` (defined at "
            "line 682 in `yt_dlp/utils/_utils.py`) with a different list-of-strings "
            "literal as `parts`. The function body is:\n"
            "```\n"
            "682: def _sanitize_path_parts(parts):\n"
            "683:     sanitized_parts = []\n"
            "684:     for part in parts:\n"
            "685:         if not part or part == '.':\n"
            "686:             continue\n"
            "687:         elif part == '..':\n"
            "688:             if sanitized_parts and sanitized_parts[-1] != '..':\n"
            "689:                 sanitized_parts.pop()\n"
            "690:             else:\n"
            "691:                 sanitized_parts.append('..')\n"
            "692:             continue\n"
            "693:         # Replace invalid segments with `#`\n"
            "694:         # - trailing dots and spaces (`asdf...` => `asdf..#`)\n"
            "695:         # - invalid chars (`<>` => `##`)\n"
            "696:         sanitized_part = re.sub(r'[/<>:\"\\|\\\\?\\*]|[\\s.]$', '#', part)\n"
            "697:         sanitized_parts.append(sanitized_part)\n"
            "699:     return sanitized_parts\n"
            "```\n\n"
            "Consider the LOOP INVARIANT to be checked at the END of every iteration "
            "body of the for-loop (line 684) -- specifically, the state of "
            "`sanitized_parts` right after one of the three terminating paths of the "
            "iteration body completes (`continue` at line 686, `continue` at line 692 "
            "after the pop/append at line 689 or 691, or fall-through after the append "
            "at line 697). The candidate invariant is:\n"
            "    INV(sanitized_parts) := all(not p.endswith('.') for p in sanitized_parts)\n"
            "i.e., NO element of the list `sanitized_parts` ends with the `.` (period) "
            "character. Note: an element equal to the literal two-character string "
            "`'..'` ends with `.` and therefore VIOLATES this invariant.\n\n"
            "Report whether this invariant is held in EVERY iteration across ALL 18 "
            "test calls. Iterations are counted per-call and summed across the suite. "
            "Return a JSON object with EXACTLY these three keys:\n"
            "- `total_iterations_observed`: int -- total number of for-loop iterations "
            "completed across all 18 test calls (i.e., for each test, the number of "
            "iterations executed by the loop on line 684, summed).\n"
            "- `violating_iteration_count`: int -- number of post-iteration snapshots in "
            "which INV(sanitized_parts) is FALSE (i.e., at least one element ends with "
            "`.`).\n"
            "- `is_invariant_always_held`: bool -- True iff "
            "`violating_iteration_count == 0`."
        ),
        "template_answer": {
            "total_iterations_observed": "int",
            "violating_iteration_count": "int",
            "is_invariant_always_held": "bool",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
