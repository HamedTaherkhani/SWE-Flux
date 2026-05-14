from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "sam_replace_local_codeuri_branch_execution_coverage"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._sam.Transform._replace_local_codeuri"
)

START_MARKER_RE = re.compile(r"\[TRACE\]\[START\]", re.MULTILINE)
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)

def _split_segments(trace_text: str) -> list[str]:
    parts = START_MARKER_RE.split(trace_text)
    return [p for p in parts[1:] if p.strip()]

def extract_covered_lines(trace_text: str) -> list[int]:
    segments = _split_segments(trace_text)
    if not segments:
        raise ValueError(
            "No [TRACE][START] markers found -- trace_plugin did not run."
        )
    if len(segments) < 15:
        raise ValueError(
            f"Expected >= 15 test segments; found {len(segments)}."
        )
    covered: set[int] = set()
    for seg in segments:
        for m in LINE_RE.finditer(seg):
            if m.group("func") != TARGET_FUNC_QUAL:
                continue
            covered.add(int(m.group("lineno")))
    return sorted(covered)

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
    covered_lines = extract_covered_lines(trace_text)

    qa = {
        "question_kind": "M1_IntraProceduralCFG",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestSamReplaceLocalCodeUriBranchExecutionCoverageQA`. "
            "The class contains 15 test methods "
            "(`test_branch_execution_case_01` through `..._case_15`). "
            "Each method calls "
            "`cfnlint.template.transforms._sam.Transform(\"foo.yaml\", "
            "template, \"us-east-1\")._replace_local_codeuri()` "
            "exactly ONCE with a per-test template constructed to "
            "exercise a specific subset of branches. "
            "QUESTION: across ALL 15 test methods, which exact "
            "line numbers inside `Transform._replace_local_codeuri` "
            "(lines 75-138 of "
            "`src/cfnlint/template/transforms/_sam.py`) are covered "
            "(emitted as `event=line`) at LEAST ONCE? Return JSON "
            "with exactly one key `covered_lines`: "
            "`{\"covered_lines\": [<int>, ...]}` where the value "
            "is a sorted list of unique integers in ascending "
            "order. "
            "Reasoning rules to simulate: "
            "(1) The function shape: lines 84-95 are the "
            "Globals/AutoPublishAlias prelude; lines 97-137 are "
            "the per-resource for-loop; the loop has FIVE "
            "sequential `if resource_type ==` heads at 103, 116, "
            "119, 124, 134 (NOT elif). "
            "(2) Always-evaluated lines on every call: 84 (get "
            "Resources), 86 (get Globals), 87 (start of multi-line "
            ".get assignment), 88 (the argument continuation -- "
            "Python emits a line event for the argument line), 90 "
            "(isinstance alias check). The closing `)` at line 89 "
            "does NOT emit a separate event. "
            "(3) Globals/alias body (90-95) only fires when "
            "`Globals.Function.AutoPublishAlias` is a 1-element "
            "Ref dict whose Ref target is in Parameters. Tests "
            "02-05 vary this prelude. "
            "(4) For-loop body (97-137) iterates per Resource. "
            "Line 100 (`if not isinstance(resource_dict, dict)`) "
            "guards `continue` at 101. After 101, lines 103+ are "
            "NOT executed for that iteration. "
            "(5) For each non-skipped iteration, ALL FIVE "
            "`if resource_type ==` heads (103, 116, 119, 124, "
            "134) are evaluated. The matching head's body runs "
            "and execution continues to subsequent heads. "
            "(6) Python's tracer emits one line event per AND "
            "clause inside a multi-line `if (A and B and C and "
            "D):` -- so lines 126, 127, 128, 129 EACH emit a "
            "separate event when reached, but the `if (` opener "
            "at line 125 and the closing `):` at line 130 do NOT. "
            "Similarly for the StateMachine `if x and y:` at lines "
            "134-136: line 134 (head + first clause) and line 135 "
            "(second clause continuation) emit, but the closing "
            "`):` at line 136 does NOT. The `else:` keyword at "
            "lines 106 and 132 also does NOT emit a separate "
            "event (only the body lines 107 and 133 do). "
            "(7) Per-test coverage by design: "
            "01: empty template -> 84, 86, 87, 90, 97; "
            "02: Globals.Function.AutoPublishAlias dict len>1 -> "
            "    91 (False); "
            "03: Globals alias = Ref to declared param -> "
            "    91, 92, 93, 94, 95; "
            "04: Globals alias = Ref to undeclared param -> "
            "    94 (False); "
            "05: Globals alias = 1-elem dict but not Ref -> "
            "    93 (False); "
            "06: Resource with non-dict Properties -> "
            "    98, 99, 100, 101 (continue); "
            "07: Function PackageType=Image -> 103, 104, 105, "
            "    108, 109, 114, 116, 119, 124, 125, 132, 133, 134; "
            "08: Function CodeUri (no PackageType) -> 104 (False), "
            "    106, 107; "
            "09: Function with AutoPublishAlias=Ref:declared -> "
            "    109 (True), 110, 111, 112, 113; "
            "10: Function with AutoPublishCodeSha256 dict -> "
            "    114 (True), 115; "
            "11: LayerVersion ContentUri -> 117 (True), 118; "
            "12: Application with Location dict -> 120, 121, "
            "    122, 123; "
            "13: Api with no DefinitionBody/Auth/Cors/"
            "    DisableExecuteApiEndpoint -> 131; "
            "14: Api with DefinitionBody present -> 132, 133; "
            "15: StateMachine with DefinitionUri -> 137. "
            "(8) NEVER covered: lines 89, 125, 130, 136 (closing "
            "parens of multi-line expressions); lines 106, 132 "
            "(else keywords); blank lines 85, 96, 102, 138; "
            "docstring lines 76-82."
        ),
        "template_answer": {
            "covered_lines": [],
        },
        "oracle_answer": {
            "covered_lines": covered_lines,
        },
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["line"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestSamReplaceLocalCodeUriBranchExecutionCoverageQA"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
