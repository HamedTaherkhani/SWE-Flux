from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "template_search_deep_keys_max_call_depth"
TARGET_FUNC_QUAL = (
    "cfnlint.template.template.Template._search_deep_keys"
)

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|return) ",
    re.MULTILINE,
)

def extract_max_depth(trace_text: str) -> int:
    depth = 0
    max_depth = 0
    for m in EVENT_RE.finditer(trace_text):
        if m.group("func") != TARGET_FUNC_QUAL:
            continue
        if m.group("event") == "call":
            depth += 1
            if depth > max_depth:
                max_depth = depth
        else:
            depth -= 1
    if max_depth == 0:
        raise ValueError(
            f"No call events for {TARGET_FUNC_QUAL!r} were observed."
        )
    return max_depth

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
    max_depth = extract_max_depth(trace_text)

    qa = {
        "question_kind": "S2_InterProceduralCFG",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestTemplateSearchDeepKeysMaxCallDepthQA`, method "
            "`test_template_search_deep_keys_max_call_depth_case`. "
            "The test instantiates "
            "`cfnlint.template.template.Template(\"foo.yaml\", _TEMPLATE, [\"us-east-1\"])`. "
            "`Template.__init__` invokes `self.search_deep_keys(...)` "
            "FIVE TIMES -- once each for the searchTexts \"Ref\", "
            "\"Fn::Sub\", \"Fn::If\", \"Fn::FindInMap\", and "
            "`FUNCTION_FOR_EACH` (a `re.Pattern`). Each "
            "`search_deep_keys` invocation calls "
            "`Template._search_deep_keys(searchText, self.template, [])` "
            "once on the template ROOT and (if `includeGlobals=True` "
            "and Globals exist) once on `self.transform_pre[\"Globals\"]`; "
            "in this run Globals is `{}`, so the second call enters "
            "the empty-dict branch and adds only depth 1. The private "
            "`_search_deep_keys` (lines 351-399 of "
            "`src/cfnlint/template/template.py`) recurses by these "
            "rules: "
            "(a) DICT cfndict: iterate keys; for each key, recurse on "
            "its value ONLY IF the value is a dict or a list. Scalar "
            "values (str/int/float/None) do NOT trigger a recursive "
            "call. "
            "(b) LIST cfndict: iterate items and recurse on EVERY "
            "item, regardless of type (string items just bottom-out "
            "without further recursion). "
            "(c) DICT cfndict whose key has a LIST value: recursion "
            "is per list item (depth +1 per item), NOT a single +1 "
            "for the list. "
            "Restricting the call-stack depth count to ONLY frames "
            "whose qualified name is "
            "`cfnlint.template.template.Template._search_deep_keys`, "
            "what is the MAXIMUM simultaneous depth of in-flight "
            "frames reached during this test run? Return the answer "
            "under the field `maximum_call_stack_depth`."
        ),
        "template_answer": {
            "maximum_call_stack_depth": "int",
        },
        "oracle_answer": {"maximum_call_stack_depth": max_depth},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["call", "return"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestTemplateSearchDeepKeysMaxCallDepthQA::"
                "test_template_search_deep_keys_max_call_depth_case"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
