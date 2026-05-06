#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# The trace plugin emits a per-line event whose `locals=...` block only contains
# the locals that *changed* since the previous line event (a diff). To recover
# the full snapshot at any line we walk events in order, accumulating values.
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/extractor/common\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.extractor\.common\._hidden_inputs) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


TARGET_FOR_LINE = "1799"
TARGET_ITERATION = 8  # 1-indexed -- "end of iter 8" means the 9th time we hit
                      # the FOR line (one initial + one per completed iter).


def extract_state(trace_text: str) -> dict:
    cumulative: dict[str, str] = {}
    for_snapshots: list[dict[str, str]] = []

    for m in LINE_RE.finditer(trace_text):
        delta = ast.literal_eval(m.group("locals"))
        cumulative.update(delta)
        if m.group("lineno") == TARGET_FOR_LINE:
            for_snapshots.append(dict(cumulative))

    if not for_snapshots:
        raise ValueError("No FOR-line events found in trace.")

    # The very first FOR event has no `input_el` bound -- it precedes iter 1.
    # The (K+1)th event is the loop-back point AFTER iteration K's body.
    target_index = TARGET_ITERATION  # 0 -> initial, 1 -> after iter 1, ...
    if len(for_snapshots) <= target_index:
        raise ValueError(
            f"Need at least {target_index + 1} FOR events, got {len(for_snapshots)}.")

    snap = for_snapshots[target_index]
    if "input_el" not in snap:
        raise ValueError(
            f"input_el not bound at FOR event #{target_index + 1}: {snap!r}")

    return {
        "input_el": ast.literal_eval(snap["input_el"]),
        "attrs": ast.literal_eval(snap["attrs"]),
        "hidden_inputs": ast.literal_eval(snap["hidden_inputs"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/extractor_hidden_inputs_loop_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/extractor_hidden_inputs_loop_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    state = extract_state(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `test/qa/extractor_hidden_inputs_loop_state_test.py`, class "
            "`TestExtractorHiddenInputsLoopStateQA`, method "
            "`test_extractor_hidden_inputs_loop_state_case`. "
            "The test calls "
            "`yt_dlp.extractor.common.InfoExtractor._hidden_inputs(HTML_FRAGMENT)` "
            "(static method defined at lines 1796-1809 in `yt_dlp/extractor/common.py`) "
            "with the exact `HTML_FRAGMENT` string shown at the top of the test file. "
            "Inside that function, line 1797 first strips HTML comments from `html`, then "
            "line 1799 begins the loop "
            "`for input_el in re.findall(r'(?i)(<input[^>]+>)', html):`. "
            "Each iteration: line 1800 calls `extract_attributes(input_el)`, line 1801 "
            "checks `if not input_el`, line 1803 checks "
            "`if attrs.get('type') not in ('hidden', 'submit')`, line 1805 binds "
            "`name = attrs.get('name') or attrs.get('id')`, line 1806 binds "
            "`value = attrs.get('value')`, and line 1807-1808 conditionally writes "
            "`hidden_inputs[name] = value`. Note that the type filter at line 1803 is "
            "case-sensitive (only literal lowercase `'hidden'` / `'submit'` match), and "
            "that `extract_attributes` decodes HTML entities. "
            "Report the state of the locals at the **end of the 8th iteration** of the for "
            "loop -- i.e., at the line-1799 trace event where `input_el` is bound to the "
            "string of the 8th matched `<input ...>` tag (the loop-back event that fires "
            "after the 8th iteration's body has fully executed and just before the 9th "
            "iteration's `input_el` is assigned). "
            "Return a JSON object with three keys: "
            "`input_el` (str, the exact text of the 8th matched input element as bound to "
            "the loop variable at that moment), "
            "`attrs` (object, the value of the `attrs` local at that moment, equal to "
            "`extract_attributes(input_el)` of the 8th match), and "
            "`hidden_inputs` (object, the exact dict accumulated through iterations 1-8 "
            "inclusive, in actual insertion order)."
        ),
        "template_answer": {
            "input_el": "str",
            "attrs": {"str": "str"},
            "hidden_inputs": {"str": "str"},
        },
        "oracle_answer": state,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
