from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "template_get_directives_outer_loop_total_iterations"
TARGET_FUNC_QUAL = "cfnlint.template.template.Template.get_directives"
TARGET_LINE = 337

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
        "question_kind": "M3_Loops",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestTemplateGetDirectivesOuterLoopTotalIterationsQA`. "
            "The class contains 15 test methods "
            "(`test_template_get_directives_outer_loop_total_iterations_case_01` "
            "through `..._case_15`). Each test method instantiates "
            "`cfnlint.template.Template(\"foo.yaml\", template, "
            "[\"us-east-1\"])` (one or more times) with templates of "
            "varying `Resources` shape, then calls "
            "`cfn.get_directives()` on each. The templates mix four "
            "kinds of `Resources` entries: "
            "(i)  fully-valid (dict with `Type`, `Properties`, and "
            "`Metadata.cfn-lint.config.ignore_checks` lists); "
            "(ii) dict-valued but WITHOUT a `Type` field; "
            "(iii) NON-dict values (e.g. a string); "
            "(iv) dict-valued with `Type: None`. "
            "QUESTION: how many times does the for-loop at line 336 "
            "of `src/cfnlint/template/template.py` "
            "(`for resource_name, resource_values in resources.items():` "
            "inside `Template.get_directives`) iterate its BODY "
            "during ONE such test method's execution? (The answer "
            "is invariant -- every one of the 15 test methods "
            "produces the same iteration count.) Return the answer "
            "under the field `total_iterations`. "
            "Reasoning rules to simulate (PER TEST): "
            "(a) The line-336 loop iterates over `resources` where "
            "`resources = self.get_resources()` (line 334). "
            "`get_resources()` (lines 180-206) does NOT return the "
            "raw `template[\"Resources\"]`; it pre-filters to "
            "include ONLY entries `(k, v)` where `isinstance(v, dict)` "
            "AND `v.get(\"Type\") is not None`. So entries (ii), "
            "(iii), and (iv) above are SILENTLY DROPPED before the "
            "loop ever sees them. "
            "(b) If `template[\"Resources\"]` is missing or "
            "non-dict, `get_resources()` returns `{}`. The "
            "`if resources:` guard at line 335 then skips the "
            "for-loop entirely -- the call contributes 0 "
            "iterations. "
            "(c) The inner for-loop at line 344 "
            "(`for ignore_rule_id in ignore_rule_ids:`) is a DECOY: "
            "it iterates over `Metadata.cfn-lint.config.ignore_checks` "
            "lists. The QUESTION targets the OUTER loop at line 336 "
            "ONLY -- inner-loop iterations DO NOT count. "
            "(d) Within the loop, `if isinstance(resource_values, "
            "dict)` at line 337 is ALWAYS true (the pre-filter "
            "guarantees this), so every iteration enters the body "
            "fully -- there is no `continue` short-circuit at the "
            "outer level. "
            "(e) Multiple `cfn.get_directives()` invocations in the "
            "same test method ADD their iter counts. "
            "(f) The total per test is the SUM over all calls of "
            "`len(self.get_resources())`, where each `self.get_resources()` "
            "evaluates the dict + has-Type filter on that call's "
            "specific `template[\"Resources\"]`."
        ),
        "template_answer": {
            "total_iterations": "int",
        },
        "oracle_answer": {"total_iterations": total_iterations},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["line"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestTemplateGetDirectivesOuterLoopTotalIterationsQA"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
