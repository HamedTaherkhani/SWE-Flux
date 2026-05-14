from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "language_extensions_foreach_value_create_dispatch"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._language_extensions._ForEachValue.create"
)

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=return retval=(?P<retval>.*?) "
    r"locals=\{",
    re.MULTILINE,
)

CLASS_RE = re.compile(
    r"<cfnlint\.template\.transforms\._language_extensions\."
    r"(?P<cls>_ForEachValue\w*) object at 0x[0-9a-fA-F]+>"
)

def extract_dispatch_chronology(trace_text: str) -> list[str]:
    sequence: list[str] = []
    for m in RETURN_RE.finditer(trace_text):
        if m.group("func") != TARGET_FUNC_QUAL:
            continue
        retval = m.group("retval")
        cm = CLASS_RE.search(retval)
        if not cm:
            raise ValueError(
                f"Could not parse class from retval repr: {retval!r}"
            )
        sequence.append(cm.group("cls"))
    if not sequence:
        raise ValueError(
            f"No event=return entries for {TARGET_FUNC_QUAL!r} found."
        )
    return sequence

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
    sequence = extract_dispatch_chronology(trace_text)

    qa = {
        "question_kind": "C2_InterProceduralCFG",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestLanguageExtensionsForEachValueCreateDispatchQA`, "
            "method "
            "`test_language_extensions_foreach_value_create_dispatch_case`. "
            "The test instantiates "
            "`cfnlint.template.transforms._language_extensions._Transform` "
            "and runs `transform(cfn)` over `_TEMPLATE`. The static "
            "factory `_ForEachValue.create(obj)` (lines 234-250 of "
            "`_language_extensions.py`) dispatches polymorphically: "
            "scalar -> `_ForEachValue`; dict whose single key is "
            "`Ref` -> `_ForEachValueRef`; `Fn::FindInMap` -> "
            "`_ForEachValueFnFindInMap`; `Fn::If` -> "
            "`_ForEachValueFnIf`; otherwise raise. Capture the EXACT "
            "concrete class type RETURNED BY EVERY CALL TO "
            "`_ForEachValue.create` IN CHRONOLOGICAL ORDER OF RETURN "
            "EVENT during this test execution. Return the answer "
            "under the field `dispatch_sequence` -- a list of class "
            "name strings (e.g. `\"_ForEachValue\"`, "
            "`\"_ForEachValueRef\"`). Subtle rules to simulate: "
            "(1) Subclass constructors themselves call `create` "
            "internally: `_ForEachValueRef.__init__` calls "
            "`create(obj)` for the inner string; "
            "`_ForEachValueFnIf.__init__` calls `create(obj[0])` for "
            "the condition name; `_ForEachValueFnFindInMap.__init__` "
            "calls `create(obj[0])`, `create(obj[1])`, `create(obj[2])` "
            "left-to-right for its list-triple. The INNER calls "
            "RETURN BEFORE the OUTER call, so the chronology is "
            "depth-first post-order at each subclass construction. "
            "(2) `_ForEach.__init__` (constructed once per outer "
            "ForEach key during template parsing) does "
            "`create(value[0])` (loop var name) and `create(item)` "
            "for each list item in the collection. "
            "(3) The TOP-LEVEL `_ForEachValueFnFindInMap` "
            "instantiated by `_walk`'s Fn::FindInMap branch is built "
            "by DIRECT constructor call -- NOT routed through "
            "`create` -- so it does NOT appear in the dispatch "
            "sequence. Only NESTED FindInMaps (one FindInMap as the "
            "argument of another) appear, because the inner one is "
            "routed through `create`. "
            "(4) `_ForEachValueFnFindInMap.value(...)` has a "
            "fallback path starting at line 366: when "
            "`t_map[1].value(...)` raises `_ResolveError` (e.g. for "
            "an `Fn::If` arg), the fallback iterates the resolved "
            "mapping and calls `_ForEachValue.create(k)` for EVERY "
            "key whose value-dict contains `t_map[2].value()`. There "
            "is NO break, so all matching keys yield a create event "
            "and the LAST one wins as the new `t_map[1]`. "
            "(5) Each iteration of the outer Fn::ForEach walks the "
            "body afresh, so the per-iteration creates duplicate "
            "across iterations in iteration order. "
            "(6) Body Properties dict iterates in INSERTION order: "
            "`Mapped` -> `Mapped2` -> `Mapped3`."
        ),
        "template_answer": {
            "dispatch_sequence": ["str"],
        },
        "oracle_answer": {"dispatch_sequence": sequence},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["return"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestLanguageExtensionsForEachValueCreateDispatchQA::"
                "test_language_extensions_foreach_value_create_dispatch_case"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
