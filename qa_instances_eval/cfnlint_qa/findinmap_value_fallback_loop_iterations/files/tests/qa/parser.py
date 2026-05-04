from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "findinmap_value_fallback_loop_iterations"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._language_extensions._ForEachValueFnFindInMap.value"
)
TARGET_LINE = 374

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)
START_MARKER_RE = re.compile(r"\[TRACE\]\[START\]", re.MULTILINE)

def _split_segments(trace_text: str) -> list[str]:
    parts = START_MARKER_RE.split(trace_text)
    return [p for p in parts[1:] if p.strip()]

def _count_iterations(segment: str) -> int:
    count = 0
    for m in LINE_RE.finditer(segment):
        if m.group("func") != TARGET_FUNC_QUAL:
            continue
        if int(m.group("lineno")) != TARGET_LINE:
            continue
        count += 1
    return count

def extract_total_iterations(trace_text: str) -> int:
    segments = _split_segments(trace_text)
    if not segments:
        raise ValueError(
            "No [TRACE][START] markers found -- trace_plugin did not run."
        )
    per_test = [_count_iterations(seg) for seg in segments]
    if len(per_test) < 15:
        raise ValueError(
            f"Expected >= 15 test segments; found {len(per_test)}: {per_test}"
        )
    distinct = set(per_test)
    if len(distinct) != 1:
        raise ValueError(
            "Per-test iteration counts diverged across the suite: "
            f"{per_test}"
        )
    return per_test[0]

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log",
    )
    parser.add_argument(
        "--out",
        default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    total_iterations = extract_total_iterations(trace_text)

    qa = {
        "question_kind": "iterations",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestFindInMapValueFallbackLoopIterationsQA`. The class "
            "contains 15 test methods "
            "(`test_findinmap_value_fallback_loop_iterations_case_01` "
            "through `..._case_15`). Each test method first resets "
            "`_language_extensions._ACCOUNT_ID = None`, then "
            "instantiates `cfnlint.template.Template(\"foo.yaml\", "
            "_TEMPLATE, [\"us-east-1\"])`, and performs a sequence of "
            "`_ForEachValueFnFindInMap(...).value(cfn, {})` invocations "
            "against the SAME `_TEMPLATE[\"Mappings\"][\"MyMap\"]` "
            "dict (8 entries). The 15 sequences vary in length (2 to "
            "5 calls) and in the Refs they pass as `t_map[1]`. The "
            "Refs used across the suite are `AWS::Region`, "
            "`AWS::AccountId`, and a variety of names that are NOT "
            "declared in `_TEMPLATE[\"Parameters\"]` (e.g. "
            "`NotInTemplate`, `MissingX`, `Phantom`, `Ghost`, etc.). "
            "QUESTION: how many times does the for-loop at line 373 "
            "of `src/cfnlint/template/transforms/_language_extensions.py` "
            "(`for k, v in cfn.template.get(\"Mappings\", {}).items():` "
            "inside `_ForEachValueFnFindInMap.value`) iterate its "
            "BODY during ONE such test method's execution? (The "
            "answer is invariant -- every one of the 15 test methods "
            "produces the same iteration count.) Return the answer "
            "under the field `total_iterations`. "
            "Reasoning rules to simulate (PER TEST): "
            "(a) The line-373 loop fires ONLY when the call to "
            "`t_map[1].value(cfn, params, only_params)` at line 368 "
            "raises `_ResolveError`. "
            "(b) `Ref: AWS::Region` resolves to `\"us-east-1\"` at "
            "lines 478-479 and does NOT raise -- the loop is "
            "SKIPPED, contributing 0 iterations. "
            "(c) `Ref: <name not in Parameters>` falls through to "
            "lines 511-513, raises `_ResolveError`, and the loop "
            "fires -- iterating EVERY entry of `mapping.items()` "
            "(no `break`), so 8 iterations. "
            "(d) `Ref: AWS::AccountId` raises `_ResolveError` while "
            "`_ACCOUNT_ID is None` (line 482-483) -- the loop fires "
            "and contributes 8 iterations. On iteration 1, line 384 "
            "latches `_ACCOUNT_ID = k` (the first mapping key) "
            "because `t_map[1]` is still a Ref-to-AWS::AccountId at "
            "that moment. After line 385 reassigns `t_map[1]` to a "
            "literal-key `_ForEachValue`, no further iterations of "
            "the SAME loop run can mutate `_ACCOUNT_ID`. "
            "(e) Once `_ACCOUNT_ID` is set, a SUBSEQUENT "
            "`Ref: AWS::AccountId` in the same test resolves "
            "cleanly via line 484, contributing 0 iterations. "
            "(f) Each test method resets `_ACCOUNT_ID = None` at "
            "entry, so latched state never leaks across tests. "
            "(g) Inside the loop, `if isinstance(v, dict)`, "
            "`if t_map_2_value in v`, and the `continue` branch at "
            "line 380 are intra-body short-circuits that do NOT cut "
            "the iteration short -- decoy entries (non-dict "
            "values, dicts without the search key, list-len <= "
            "max_length entries) all still count."
        ),
        "template_answer": {
            "total_iterations": "int",
        },
        "oracle_answer": {"total_iterations": total_iterations},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["line"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestFindInMapValueFallbackLoopIterationsQA"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
