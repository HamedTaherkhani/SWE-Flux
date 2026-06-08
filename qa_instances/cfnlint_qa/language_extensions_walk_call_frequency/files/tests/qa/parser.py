from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "language_extensions_walk_call_frequency"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._language_extensions._Transform._walk"
)

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call ",
    re.MULTILINE,
)

def extract_call_count(trace_text: str) -> int:
    return sum(
        1 for m in CALL_RE.finditer(trace_text)
        if m.group("func") == TARGET_FUNC_QUAL
    )

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
    count = extract_call_count(trace_text)
    if count == 0:
        raise ValueError(
            f"No event=call lines for {TARGET_FUNC_QUAL!r} found in the trace log."
        )

    qa = {
        "question_kind": "S2_InterProceduralCFG",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestLanguageExtensionsWalkCallFrequencyQA`, method "
            "`test_language_extensions_walk_call_frequency_case`. The "
            "test instantiates "
            "`cfnlint.template.transforms._language_extensions._Transform` "
            "and runs `transform(cfn)` over `_TEMPLATE`. The single "
            "outermost dispatch is `_walk(cfn.template, {}, cfn)` "
            "(line 108 of `_language_extensions.py`); `_walk` then "
            "recursively walks the template per the rules at "
            "lines 111-198. EXACTLY how many times is "
            "`cfnlint.template.transforms._language_extensions._Transform._walk` "
            "invoked during this test run? Count every `_walk` "
            "invocation including the outermost call. Dispatch rules "
            "(by FIRST dict key): "
            "(1) `Fn::ForEach::<...>`: iterate the literal-list "
            "collection in order, recurse on the iteration body with "
            "`params` extended by the loop var, merge each returned "
            "dict into `obj`, then DELETE the `Fn::ForEach` key. "
            "(2) `Fn::Sub` with a STRING value: run "
            "`_replace_string_params(v, params)`; if fully resolved, "
            "REPLACE the `Fn::Sub` dict with the string. NO recursive "
            "`_walk` is performed by this branch. "
            "(3) `Fn::Sub` with a LIST value: run "
            "`_replace_string_params(v[0], params)`; if fully "
            "resolved, return that string IMMEDIATELY (NO recursion "
            "on v[1]); otherwise keep the dict and recursively walk "
            "v[1] (the inline-substitution object). "
            "(4) `Fn::FindInMap`: instantiate "
            "`_ForEachValueFnFindInMap` and call `.value(...)`; on "
            "success (a scalar/list) return it IMMEDIATELY (NO "
            "recursion on v); on ANY exception, recursively walk EACH "
            "element of v (so for a 3-element FindInMap, that adds 3 "
            "extra _walk calls). "
            "(5) `Ref` with STRING value: if `v in params`, return "
            "`params[v]` IMMEDIATELY (no recursion); otherwise leave "
            "the dict unchanged. "
            "(6) Any other key: recursively walk the value; if the "
            "sub-walk returns `None`, delete the key. This applies to "
            "`Transform`, `Mappings`, `Resources`, `Type`, "
            "`Properties`, `BucketName`, `Mapped`, `Tags`, `Key`, "
            "`Value`, etc. Dispatch happens AFTER the per-key "
            "${var}-rename pass (line 116-120) which itself does NOT "
            "invoke `_walk`. "
            "(7) On a list, walk each element in place. "
            "(8) Strings, ints, floats and bools count as ONE call each "
            "(deepcopy-and-return tail). "
            "Note: per-iteration of ForEach, the body dict is walked "
            "fresh (deepcopy at the top of `_walk`). The Mappings "
            "block is walked just once -- the FindInMap resolver "
            "reads it directly without invoking `_walk`. Return the "
            "answer as the field `function_call_count`."
        ),
        "template_answer": {
            "function_call_count": "int",
        },
        "oracle_answer": {"function_call_count": count},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["call"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestLanguageExtensionsWalkCallFrequencyQA::"
                "test_language_extensions_walk_call_frequency_case"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
