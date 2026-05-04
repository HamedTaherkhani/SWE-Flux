from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "foreach_value_ref_branch_execution_coverage"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._language_extensions._ForEachValueRef.value"
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
        "question_kind": "coverage_prediction",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestForEachValueRefBranchExecutionCoverageQA`. The "
            "class contains 15 test methods "
            "(`test_branch_execution_case_01` through "
            "`..._case_15`). Each method instantiates "
            "`cfnlint.template.Template(\"foo.yaml\", template_dict, "
            "[region])` with a per-test region and Parameters dict, "
            "then constructs "
            "`_ForEachValueRef(get_hash(ref_name), ref_name)` and "
            "calls `.value(cfn, runtime_params)` exactly ONCE. The "
            "(region, ref_name, parameters, runtime_params) tuple "
            "varies per test to deliberately exercise a SUBSET of "
            "the conditional branches inside "
            "`_ForEachValueRef.value` (lines 452-531 of "
            "`src/cfnlint/template/transforms/_language_extensions.py`). "
            "QUESTION: across ALL 15 test methods, which exact "
            "line numbers inside `_ForEachValueRef.value` are "
            "covered (i.e., emitted as `event=line`) at LEAST ONCE? "
            "Return JSON with exactly one key `covered_lines`: "
            "`{\"covered_lines\": [<int>, ...]}` where the value "
            "is a sorted list of unique integers in ascending "
            "order. "
            "Reasoning rules to simulate (per-test): "
            "(1) `_drive_value(region, ref_name, parameters, "
            "runtime_params)` builds a fresh "
            "`Template(\"foo.yaml\", {\"Parameters\": parameters or "
            "{}, \"Resources\": {\"Bucket\": {\"Type\": "
            "\"AWS::S3::Bucket\"}}}, [region])` and calls "
            "`_ForEachValueRef(get_hash(ref_name), "
            "ref_name).value(cfn, runtime_params)`. "
            "(2) Inside `.value`: line 458 evaluates `if params is "
            "None:`. If True, line 459 sets `params = {}`. Line "
            "460 calls `self._ref.value(cfn, params)` -> returns "
            "the string `ref_name`. Line 462 evaluates `if not "
            "isinstance(v, str):` (always False here). Line 465 "
            "evaluates `if v in params:`. If True, line 466 returns "
            "early -- nothing else in the function runs. "
            "(3) Otherwise the function continues to lines 468 (if "
            "only_params -- always False here), 471 (region = "
            "cfn.regions[0]), 472 (account_id), 473 (partition = "
            "\"aws\"), 474 (if region in gov pair), 475 (gov "
            "partition assignment -- only entered when region is "
            "us-gov-east-1 / us-gov-west-1), 476 (if region in cn "
            "pair), 477 (cn partition assignment -- only entered "
            "when region is cn-north-1 / cn-northwest-1). "
            "(4) Then the AWS::* dispatch chain at 478, 481, 486, "
            "489, 492, 495, 502, 505. The HEAD of each `if` is "
            "evaluated until one matches; matched body runs, then "
            "the function returns -- subsequent if-heads are NOT "
            "evaluated. "
            "(5) For ref_names not matching any AWS::*: lines "
            "511-531 do parameter resolution. Line 511 fetches "
            "`p = cfn.template.get(\"Parameters\", {}).get(v)`. "
            "Line 512 (`if not p:`) raises at 513 if `p` is None. "
            "Otherwise lines 514, 515 (`if t.startswith(\"AWS::SSM::"
            "Parameter\")`), 517 (default = p.get(\"Default\")), "
            "518 (`if default:`). If default truthy: line 519 "
            "(`if \"List\" in t:`) -- 520 returns split list, "
            "521 returns default. Else lines 522 (allowed_values), "
            "523 (`if len(allowed_values) > 0:`). If True: line 524 "
            "(`if \"List\" in t:`) -- 525 returns split list, "
            "526 returns allowed_values[0]. Else line 528 "
            "(`if \"List\" in t:`) -- 529 returns Fn::Select chain, "
            "or line 531 raises. "
            "(6) Branches NEVER exercised by any of the 15 tests: "
            "`AWS::AccountId` (lines 482-484), "
            "`AWS::NotificationARNs` (line 487), the SSM::Parameter "
            "raise (line 516), the no-parameter-declared raise "
            "(line 513), and the final raise (line 531). "
            "(7) Per-test test methods cover: "
            "01: us-east-1+AWS::Region; "
            "02: us-gov-east-1+AWS::Region (covers 475); "
            "03: cn-north-1+AWS::Region (covers 477); "
            "04: us-east-1+AWS::Partition; "
            "05: us-east-1+AWS::StackId; "
            "06: us-east-1+AWS::StackName; "
            "07: us-east-1+AWS::URLSuffix (returns 'amazonaws.com'); "
            "08: cn-north-1+AWS::URLSuffix (covers 477 + returns "
            "'amazonaws.com.cn'); "
            "09: us-east-1+AWS::NoValue; "
            "10: us-east-1+ref='Foo' with runtime_params={'Foo': "
            "'bar'} -- early return at line 466; "
            "11: ref='MyParam', Default='v', Type='String'; "
            "12: ref='MyListParam', Default='a,b,c', "
            "Type='CommaDelimitedList'; "
            "13: ref='MyAllowed', AllowedValues=['x','y'], "
            "Type='String', no Default; "
            "14: ref='MyAllowedList', "
            "AllowedValues=['a,b','c,d'], Type='CommaDelimitedList', "
            "no Default; "
            "15: ref='MyListNoData', Type='CommaDelimitedList', no "
            "Default, no AllowedValues."
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
                "tests/qa/testcase.py::TestForEachValueRefBranchExecutionCoverageQA"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
