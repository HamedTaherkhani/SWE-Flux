from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

INSTANCE_ID = "transform_walk_foreach_outer_state"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._language_extensions._Transform._walk"
)

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=return retval=(?P<retval>.*?) "
    r"locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

def extract_outer_retval(trace_text: str):
    matches = [
        m for m in RETURN_RE.finditer(trace_text)
        if m.group("func") == TARGET_FUNC_QUAL
    ]
    if not matches:
        raise ValueError(
            f"No return events for {TARGET_FUNC_QUAL!r} found in the trace log."
        )

    last = matches[-1]
    retval = ast.literal_eval(last.group("retval"))
    if not isinstance(retval, dict):
        raise ValueError(
            "Expected the outermost _walk retval to parse into a dict, got: "
            f"{type(retval).__name__}"
        )
    return retval

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
    walked = extract_outer_retval(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestTransformWalkForeachOuterStateQA`, method "
            "`test_transform_walk_foreach_outer_state_case`. The test "
            "drives "
            "`cfnlint.template.transforms._language_extensions._Transform.transform(cfn)` "
            "over `_TEMPLATE`. The transformer's recursive workhorse "
            "is `_Transform._walk(item, params, cfn)` (defined at "
            "line 111 of "
            "`src/cfnlint/template/transforms/_language_extensions.py`). "
            "Capture the EXACT value returned by the OUTERMOST call to "
            "`_walk` (item=cfn.template, params={}). The dispatch "
            "rules to simulate, by FIRST dict key: "
            "(1) `Fn::ForEach::<...>`: instantiate `_ForEach`, "
            "iterate the literal-list collection in order, recurse on "
            "the iteration body with `params` extended by the loop "
            "var, merge each returned dict into `obj`, then DELETE "
            "the `Fn::ForEach` key. "
            "(2) `Fn::Sub` with a string value: run "
            "`_replace_string_params(v, params)`; if fully resolved, "
            "REPLACE the entire `Fn::Sub` dict with the resolved "
            "string. "
            "(3) `Fn::Sub` with a list value: run "
            "`_replace_string_params(v[0], params)`; if fully "
            "resolved, return that string; OTHERWISE keep the dict "
            "and recursively walk `v[1]` (the inline-substitution "
            "object). "
            "(4) `Fn::FindInMap`: instantiate "
            "`_ForEachValueFnFindInMap` and call `.value(...)`; on "
            "success return the scalar/list directly; on ANY "
            "exception, recursively walk EACH element of `v` (so a "
            "`Ref: Letter` inside `v` resolves to the iteration "
            "value) and keep the `Fn::FindInMap` key with the "
            "(partially) walked list. "
            "(5) `Ref` with string value: if `v in params`, return "
            "`params[v]` directly (the entire `{Ref: ...}` dict is "
            "replaced by the parameter value); otherwise leave the "
            "dict unchanged. "
            "(6) Key with `${var}` text: when `params` is non-empty, "
            "rename via `_replace_string_params` BEFORE the dispatch "
            "loop runs. "
            "(7) For any non-special key, recursively walk the value; "
            "if the sub-walk returns `None`, delete the key. "
            "(8) On a list, walk each element in place. Strings, "
            "ints, etc. are returned unchanged via the deepcopy at "
            "the top of `_walk`. "
            "Note: `${var}` inside an ORDINARY string value is NOT "
            "substituted -- only inside dict KEYS or inside an "
            "`Fn::Sub` dict. Return the answer as the field "
            "`outer_walk_retval` whose value is the full transformed "
            "template dict produced by the outer `_walk` call. "
            "Preserve dict insertion order at every level."
        ),
        "template_answer": {
            "outer_walk_retval": {"<key>": "<value>"},
        },
        "oracle_answer": {
            "outer_walk_retval": walked,
        },
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["return"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestTransformWalkForeachOuterStateQA::"
                "test_transform_walk_foreach_outer_state_case"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
