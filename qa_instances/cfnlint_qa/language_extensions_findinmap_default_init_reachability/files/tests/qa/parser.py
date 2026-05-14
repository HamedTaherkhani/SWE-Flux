from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "language_extensions_findinmap_default_init_reachability"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._language_extensions._FnFindInMapDefaultValue.__init__"
)

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call ",
    re.MULTILINE,
)

def extract_reachability(trace_text: str) -> bool:
    for m in CALL_RE.finditer(trace_text):
        if m.group("func") == TARGET_FUNC_QUAL:
            return True
    return False

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
    reached = extract_reachability(trace_text)

    qa = {
        "question_kind": "C1_IntraProceduralCFG",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestLanguageExtensionsFindInMapDefaultInitReachabilityQA`, "
            "method "
            "`test_language_extensions_findinmap_default_init_reachability_case`. "
            "The test instantiates "
            "`cfnlint.template.transforms._language_extensions._Transform` "
            "and runs `transform(cfn)` over `_TEMPLATE`. Question: "
            "during this test execution, is "
            "`cfnlint.template.transforms._language_extensions._FnFindInMapDefaultValue.__init__` "
            "EVER called (one or more times)? Return the answer "
            "under the field `is_reached` as a boolean. "
            "Reasoning rules to simulate: "
            "(1) `_FnFindInMapDefaultValue.__init__` is invoked at "
            "line 312 of `_language_extensions.py`, INSIDE "
            "`_ForEachValueFnFindInMap.__init__`, ONLY when the "
            "Fn::FindInMap argument list has length 4 (the optional "
            "DefaultValue object). "
            "(2) `_ForEachValueFnFindInMap.__init__` itself is invoked "
            "either directly by `_walk` (its `Fn::FindInMap` dispatch "
            "arm at line 161-174) or transitively when "
            "`_ForEachValue.create({\"Fn::FindInMap\": [...]})` is "
            "called (e.g. for a nested FindInMap). Either way, the "
            "FindInMap dict must be REACHED by `_walk`. "
            "(3) `_walk`'s `Fn::ToJsonString` dispatch arm at line "
            "141-143 short-circuits: it returns the deepcopied dict "
            "WITHOUT recursing into the value. So any FindInMap "
            "buried inside an `Fn::ToJsonString` value is never "
            "walked, never constructed, and DefaultValue.__init__ is "
            "never reached from there. "
            "(4) A 3-element FindInMap (no DefaultValue) does NOT "
            "trigger DefaultValue.__init__, regardless of how many "
            "times the FindInMap itself is constructed -- the "
            "`if len(obj) == 4:` guard at line 311 prevents it. "
            "(5) The Fn::ForEach iteration walks the body once per "
            "collection element."
        ),
        "template_answer": {
            "is_reached": "bool",
        },
        "oracle_answer": {"is_reached": reached},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["call"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestLanguageExtensionsFindInMapDefaultInitReachabilityQA::"
                "test_language_extensions_findinmap_default_init_reachability_case"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
