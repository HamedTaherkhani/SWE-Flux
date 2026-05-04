from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "findinmap_value_account_id_cache_path_determinism"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._language_extensions._ForEachValueFnFindInMap.value"
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

def _extract_sequence(segment: str) -> tuple[int, ...]:
    seq: list[int] = []
    for m in LINE_RE.finditer(segment):
        if m.group("func") != TARGET_FUNC_QUAL:
            continue
        seq.append(int(m.group("lineno")))
    return tuple(seq)

def extract_invariant(trace_text: str) -> bool:
    segments = _split_segments(trace_text)
    if not segments:
        raise ValueError(
            "No [TRACE][START] markers found -- trace_plugin did not run."
        )
    if len(segments) < 15:
        raise ValueError(
            f"Expected >= 15 test segments; found {len(segments)}."
        )
    sequences = []
    for idx, seg in enumerate(segments, 1):
        s = _extract_sequence(seg)
        if not s:
            raise ValueError(
                f"No event=line entries for {TARGET_FUNC_QUAL!r} in "
                f"segment {idx} -- did the test invoke the target?"
            )
        sequences.append(s)
    return len(sequences) == len(segments) and len(set(sequences)) == 1

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
    invariant_exists = extract_invariant(trace_text)

    qa = {
        "question_kind": "determinism_flakiness",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestFindInMapValueAccountIdCachePathDeterminismQA`. "
            "The class contains 15 syntactically-identical test "
            "methods "
            "(`test_findinmap_value_account_id_cache_path_determinism_case_01` "
            "through `..._case_15`). Each method instantiates "
            "`cfnlint.template.Template(\"foo.yaml\", _TEMPLATE, "
            "[\"us-east-1\"])` and calls "
            "`_ForEachValueFnFindInMap(get_hash(_FIM_OBJ), "
            "_FIM_OBJ).value(cfn, {})` exactly ONCE with the SAME "
            "`_FIM_OBJ = [\"MyMap\", {\"Ref\": \"AWS::AccountId\"}, "
            "\"v\"]` and the SAME `_TEMPLATE` (8-entry MyMap "
            "Mapping; empty Parameters block). "
            "CRITICAL: NO test method resets the module-level "
            "`cfnlint.template.transforms._language_extensions._ACCOUNT_ID` "
            "between calls. The 15 methods run sequentially within "
            "the SAME pytest process, sharing the module import. "
            "QUESTION: do all 15 sequential executions of "
            "`_ForEachValueFnFindInMap.value` follow the EXACT SAME "
            "sequence of executed line numbers inside that target "
            "function? Return JSON with exactly one key: "
            "`{\"invariant_exists\": <bool>}`. "
            "Reasoning rules to simulate: "
            "(1) Inside `_ForEachValueFnFindInMap.value`, line 366 "
            "checks `if mapping:` (mapping = MyMap's contents, "
            "non-None), entering the inner try at line 367. "
            "(2) Line 368 calls `t_map[1].value(cfn, params, "
            "only_params)`, which is `_ForEachValueRef.value` for "
            "the `AWS::AccountId` Ref. "
            "(3) `_ForEachValueRef.value` lines 481-484 of "
            "`_language_extensions.py`: "
            "    `if v == \"AWS::AccountId\": "
            "        if _ACCOUNT_ID is None: raise _ResolveError(...) "
            "        return _ACCOUNT_ID`. "
            "(4) On the FIRST test method (`_case_01`), nothing has "
            "mutated module-global `_ACCOUNT_ID` since import time, "
            "so `_ACCOUNT_ID is None` and line 483 raises. The "
            "outer except at line 369 catches it and the fallback "
            "for-loop at line 373 is entered. The loop iterates ALL "
            "8 mapping entries; on iteration 1 (k=`\"111111111111\"`), "
            "line 384 latches `_ACCOUNT_ID = \"111111111111\"` "
            "(because `t_map[1]` is still a Ref-to-AWS::AccountId). "
            "(5) On test methods `_case_02` through `_case_15`, "
            "`_ACCOUNT_ID == \"111111111111\"` (latched by "
            "`_case_01`). Line 484 returns the cached value cleanly "
            "-- NO `_ResolveError`, NO entry into the line-370-389 "
            "fallback block, NO line-373 for-loop. Execution "
            "proceeds directly from line 368 to line 391 then 393-398. "
            "(6) The line-number sequence INSIDE "
            "`_ForEachValueFnFindInMap.value` is therefore "
            "DRAMATICALLY DIFFERENT for `_case_01` (long, with "
            "8-iter loop) versus `_case_02..._case_15` (short, no "
            "loop). The 15 per-test sequences are NOT all "
            "identical -- the path-determinism invariant does NOT "
            "hold."
        ),
        "template_answer": {
            "invariant_exists": "bool",
        },
        "oracle_answer": {
            "invariant_exists": invariant_exists,
        },
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["line"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestFindInMapValueAccountIdCachePathDeterminismQA"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
