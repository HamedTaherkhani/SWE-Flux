from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

INSTANCE_ID = "findinmap_value_fallback_max_length_condition_snapshot"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._language_extensions._ForEachValueFnFindInMap.value"
)
TARGET_LINE = 378

START_MARKER_RE = re.compile(r"\[TRACE\]\[START\]", re.MULTILINE)
EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line locals=(?P<locals>\{.*\})\s*$"
)

def _split_segments(trace_text: str) -> list[str]:
    parts = START_MARKER_RE.split(trace_text)
    return [p for p in parts[1:] if p.strip()]

def _parse_locals(locals_str: str) -> dict[str, object]:
    raw = ast.literal_eval(locals_str)
    out: dict[str, object] = {}
    for k, v_repr in raw.items():
        if not isinstance(v_repr, str):
            out[k] = v_repr
            continue
        try:
            out[k] = ast.literal_eval(v_repr)
        except (ValueError, SyntaxError):
            out[k] = v_repr
    return out

def _snapshot_from_segment(segment: str) -> list:
    accum: dict[str, object] = {}
    for raw_line in segment.splitlines():
        m = EVENT_RE.match(raw_line)
        if not m:
            continue
        if m.group("func") != TARGET_FUNC_QUAL:
            continue
        delta = _parse_locals(m.group("locals"))
        accum.update(delta)
        if int(m.group("lineno")) == TARGET_LINE:
            break
    else:
        raise ValueError(
            f"No line={TARGET_LINE} event for {TARGET_FUNC_QUAL!r} found "
            f"in segment."
        )

    if "t_map_2_value" not in accum or "v" not in accum or "max_length" not in accum:
        raise ValueError(
            f"Missing required locals in accumulated state: "
            f"{sorted(accum.keys())}"
        )
    t_map_2_value = accum["t_map_2_value"]
    v = accum["v"]
    max_length = accum["max_length"]
    inner = v[t_map_2_value] if isinstance(v, dict) and t_map_2_value in v else None
    return [
        t_map_2_value,
        isinstance(inner, list),
        len(inner) if isinstance(inner, list) else None,
        max_length,
    ]

def extract_snapshot(trace_text: str) -> list:
    segments = _split_segments(trace_text)
    if not segments:
        raise ValueError(
            "No [TRACE][START] markers found -- trace_plugin did not run."
        )
    if len(segments) < 15:
        raise ValueError(
            f"Expected >= 15 test segments; found {len(segments)}."
        )
    snapshots = [_snapshot_from_segment(seg) for seg in segments]
    distinct = {tuple(s) for s in snapshots}
    if len(distinct) != 1:
        raise ValueError(
            f"Expected all 15 snapshots identical; found {len(distinct)} "
            f"distinct snapshots: {distinct}"
        )
    return snapshots[0]

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
    snapshot = extract_snapshot(trace_text)

    qa = {
        "question_kind": "M4_ProgramState",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestFindInMapValueFallbackMaxLengthConditionSnapshotQA`. "
            "The class contains 15 test methods "
            "(`test_snapshot_case_01` through `..._case_15`). Each "
            "method calls a helper that (1) sets module-global "
            "`cfnlint.template.transforms._language_extensions._ACCOUNT_ID = None`, "
            "(2) builds `cfnlint.template.Template(\"foo.yaml\", "
            "{\"Mappings\": {<mapping_name>: <mapping_dict>}, "
            "\"Parameters\": {}, \"Resources\": {\"Bucket\": "
            "{\"Type\": \"AWS::S3::Bucket\"}}}, [\"us-east-1\"])`, "
            "and (3) calls "
            "`_ForEachValueFnFindInMap(get_hash(fim_obj), "
            "fim_obj).value(cfn, {})` exactly ONCE with "
            "`fim_obj = [<mapping_name>, {\"Ref\": "
            "\"AWS::AccountId\"}, \"v\"]`. The 15 tests vary the "
            "`mapping_name`, the FIRST-key name in `mapping_dict`, "
            "and the trailing decoy entries -- but every test "
            "arranges for the FIRST entry of `mapping_dict` to be "
            "`{<some_name>: {\"v\": [\"a\", \"b\"]}}` (a dict whose "
            "`\"v\"` is a 2-element list). "
            "TARGET CONDITION: lines 376-379 of "
            "`src/cfnlint/template/transforms/_language_extensions.py`, "
            "inside `_ForEachValueFnFindInMap.value`: "
            "`if (isinstance(v[t_map_2_value], list) and "
            "len(v[t_map_2_value]) <= max_length):`. The line=378 "
            "AND-clause check is the precise evaluation point. "
            "QUESTION: at the EXACT FIRST evaluation of the line-378 "
            "AND-clause during a test (which is the same across all "
            "15 tests by design), what are the values of "
            "`(t_map_2_value, isinstance(v[t_map_2_value], list), "
            "len(v[t_map_2_value]), max_length)`? Return JSON with "
            "exactly one key: `{\"snapshot\": [<value>, <value>, "
            "<value>, <value>]}`. "
            "Reasoning rules to simulate: "
            "(1) Each test sets `_ACCOUNT_ID = None` at start. "
            "(2) `_ForEachValueFnFindInMap.value` runs: "
            "lines 323-325 init `params={}` and "
            "`t_map = deepcopy(self._map)` (3 elements: "
            "`_ForEachValue(\"<mapping_name>\")`, "
            "`_ForEachValueRef(\"AWS::AccountId\")`, "
            "`_ForEachValue(\"v\")`). "
            "(3) Lines 327-330: `mapping = "
            "cfn.template.get(\"Mappings\", {}).get(\"<mapping_name>\")` "
            "-- non-None, equals the `mapping_dict`. "
            "(4) Lines 337-348 (first try): condition `mapping is "
            "None` is False -> body skipped. "
            "(5) Lines 350-364 (second try): same -> skipped. "
            "(6) Line 366: `if mapping:` -- True. Line 367 try: "
            "`t_map[1].value(cfn, params, only_params)` calls "
            "`_ForEachValueRef.value(cfn, {}, False)`. Inside that "
            "call (lines 458+), `v = \"AWS::AccountId\"`, line 481 "
            "matches, line 482 `if _ACCOUNT_ID is None:` is True, "
            "line 483 raises `_ResolveError`. "
            "(7) Line 369 except catches; enters fallback at line "
            "370. Line 371: `t_map_2_value = "
            "t_map[2].value(cfn, params, only_params)` -- "
            "`t_map[2]` is `_ForEachValue(\"v\")`, returns the "
            "string `\"v\"`. "
            "(8) Line 372: `max_length = -1`. "
            "(9) Line 373: `for k, v in mapping.items():` -- "
            "Python 3.7+ dict insertion order. The first iteration "
            "binds `(k, v)` to the FIRST entry of `mapping_dict`. "
            "By construction of the suite, that first entry is "
            "`{<first_key>: {\"v\": [\"a\", \"b\"]}}`. So `v = "
            "{\"v\": [\"a\", \"b\"]}`. "
            "(10) Line 374: `if isinstance(v, dict):` -- True. "
            "(11) Line 375: `if t_map_2_value in v:` -- "
            "`\"v\" in {\"v\": [\"a\", \"b\"]}` is True. "
            "(12) Line 376-379: the AND-clause is evaluated. "
            "`isinstance(v[t_map_2_value], list)` is "
            "`isinstance([\"a\", \"b\"], list)` -> True. "
            "`len(v[t_map_2_value])` is `len([\"a\", \"b\"])` -> 2. "
            "`max_length` is still `-1` (unchanged on iter 1). "
            "(13) The snapshot at this evaluation moment is "
            "`(\"v\", True, 2, -1)`. "
            "(14) Trailing decoy entries (different shapes) are "
            "iterated AFTER the snapshot moment, so they cannot "
            "change the snapshot. "
            "Hardness: an LLM that misses the `_ACCOUNT_ID` reset "
            "will reason about the cached-fast path and never reach "
            "line 378. An LLM that assumes `max_length = 0` will "
            "get the 4th element wrong. An LLM that confuses "
            "`v[t_map_2_value]` with `v` will get the 3rd element "
            "wrong (`len({\"v\": [\"a\", \"b\"]})` is 1, not 2)."
        ),
        "template_answer": {
            "snapshot": [None, None, None, None],
        },
        "oracle_answer": {
            "snapshot": snapshot,
        },
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["line"],
            "target_line": TARGET_LINE,
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestFindInMapValueFallbackMaxLengthConditionSnapshotQA"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
