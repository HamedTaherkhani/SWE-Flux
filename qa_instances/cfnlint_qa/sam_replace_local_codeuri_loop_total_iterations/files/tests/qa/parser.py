from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "sam_replace_local_codeuri_loop_total_iterations"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._sam.Transform._replace_local_codeuri"
)
TARGET_LINE = 98

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
            "`TestSamReplaceLocalCodeUriLoopTotalIterationsQA`. The "
            "class contains 15 test methods "
            "(`test_sam_replace_local_codeuri_loop_total_iterations_case_01` "
            "through `..._case_15`). Each test method instantiates "
            "`cfnlint.template.transforms._sam.Transform(\"foo.yaml\", "
            "template, \"us-east-1\")` and calls "
            "``t._replace_local_codeuri()`` with templates of varying "
            "shape: different `Resources` sizes (0 to 10), different "
            "resource Types (`AWS::S3::Bucket`, "
            "`AWS::Serverless::Function`, `AWS::Serverless::Api`, "
            "`AWS::Serverless::LayerVersion`, mixes), different "
            "`Properties` shapes (dicts, missing, non-dict scalars), "
            "and different call counts (1 to 10). None of the "
            "templates set `Globals/Function/AutoPublishAlias`, so "
            "the inner decoy loop at line 92 never fires. "
            "QUESTION: how many times does the for-loop at line 97 "
            "of `src/cfnlint/template/transforms/_sam.py` "
            "(`for _, rsc in all_resources.items():` inside "
            "`Transform._replace_local_codeuri`) iterate its BODY "
            "during ONE such test method's execution? (The answer "
            "is invariant -- every one of the 15 test methods "
            "produces the same iteration count.) Return the answer "
            "under the field `total_iterations`. "
            "Reasoning rules to simulate (PER TEST): "
            "(a) The line-97 loop iterates EXACTLY "
            "`len(self._template.get(\"Resources\", {}))` times per "
            "call. If `Resources` is missing, `template.get(\"Resources\", {})` "
            "returns `{}` and the loop iterates 0 times. If "
            "`Resources` is present but empty, same -- 0 iterations. "
            "(b) The `continue` at line 101 (when "
            "`isinstance(rsc.get(\"Properties\"), dict)` is False) "
            "does NOT reduce the iter count -- the iteration still "
            "counts; the body just bails before any branch. "
            "(c) Resource `Type` values that don't match any of "
            "the SAM `if resource_type == ...` chains (e.g. "
            "`AWS::S3::Bucket`, `AWS::DynamoDB::Table`, ...) cause "
            "every branch to be false; the body completes without "
            "mutation but the iteration STILL counts. "
            "(d) The line-92 for-loop (`for k, v in "
            "auto_publish_alias.items():`) is gated by "
            "`Globals/Function/AutoPublishAlias` being a 1-element "
            "dict -- none of the test fixtures set Globals, so this "
            "loop NEVER fires and is irrelevant to the answer. "
            "(e) Multiple `Transform(...)._replace_local_codeuri()` "
            "invocations in the same test method ADD their iter "
            "counts. "
            "(f) The total per test is the SUM over all calls of "
            "`len(template.get(\"Resources\", {}))`."
        ),
        "template_answer": {
            "total_iterations": "int",
        },
        "oracle_answer": {"total_iterations": total_iterations},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["line"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestSamReplaceLocalCodeUriLoopTotalIterationsQA"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
