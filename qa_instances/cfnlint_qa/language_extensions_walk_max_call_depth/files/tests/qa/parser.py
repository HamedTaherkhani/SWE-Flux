from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "language_extensions_walk_max_call_depth"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._language_extensions._Transform._walk"
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
            "`TestLanguageExtensionsWalkMaxCallDepthQA`, method "
            "`test_language_extensions_walk_max_call_depth_case`. The "
            "test instantiates "
            "`cfnlint.template.transforms._language_extensions._Transform` "
            "and runs `transform(cfn)` over `_TEMPLATE`. The single "
            "outermost dispatch is `_walk(cfn.template, {}, cfn)` "
            "(line 108 of `_language_extensions.py`); `_walk` then "
            "recursively walks the template per the rules at "
            "lines 111-198. Restricting the call-stack depth count to "
            "ONLY frames whose qualified name is "
            "`cfnlint.template.transforms._language_extensions._Transform._walk`, "
            "what is the MAXIMUM simultaneous depth of in-flight "
            "`_walk` frames reached during this test run? Dispatch "
            "rules (by FIRST dict key): "
            "(1) `Fn::ForEach::<...>`: iterate the literal-list "
            "collection in order and recurse on the iteration body "
            "with `params` extended by the loop var (one new `_walk` "
            "frame per iteration). After all iterations, DELETE the "
            "`Fn::ForEach` key. "
            "(2) `Fn::Sub` with a STRING value: run "
            "`_replace_string_params(v, params)`; if fully resolved, "
            "REPLACE the dict with the string. NO recursive `_walk`. "
            "(3) `Fn::Sub` with a LIST value: run "
            "`_replace_string_params(v[0], params)`; if fully "
            "resolved, return that string IMMEDIATELY (no recursion "
            "on v[1]); otherwise keep the dict and recursively walk "
            "v[1]. "
            "(4) `Fn::FindInMap`: instantiate "
            "`_ForEachValueFnFindInMap` and call `.value(...)`; on "
            "success (a scalar/list) return it IMMEDIATELY (no "
            "recursion on v); on ANY exception, recursively walk EACH "
            "element of v. "
            "(5) `Ref` with STRING value: if `v in params`, return "
            "`params[v]` IMMEDIATELY (no further recursion BUT the "
            "`_walk` frame for the dict containing `Ref` is still "
            "entered, so it counts toward depth). "
            "(6) Any other key: recursively walk the value; if the "
            "sub-walk returns `None`, delete the key. Each recursion "
            "adds one `_walk` frame. "
            "(7) On a list, walk each element in place (one `_walk` "
            "frame per element). "
            "(8) Strings, ints, floats and bools enter ONE `_walk` "
            "frame each (deepcopy-and-return tail). "
            "Note: the per-key ``${var}``-rename pass at lines 115-120 "
            "does NOT itself invoke `_walk` -- only `_replace_string_params` "
            "is called. Return the answer as the field "
            "`maximum_call_stack_depth`."
        ),
        "template_answer": {
            "maximum_call_stack_depth": "int",
        },
        "oracle_answer": {"maximum_call_stack_depth": max_depth},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["call", "return"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestLanguageExtensionsWalkMaxCallDepthQA::"
                "test_language_extensions_walk_max_call_depth_case"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
