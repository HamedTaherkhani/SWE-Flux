from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT_DIR = Path("/testbed")
TARGET_FILE_SUFFIX = "cfnlint/jsonschema/_keywords.py"
TARGET_FUNC_QUAL = "cfnlint.jsonschema._keywords.contains"
INSTANCE_ID = "contains_matches_max_contains_loop_invariant_suite"
TARGET_LINE = 142

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>\w+) ",
)

def _is_target_path(path: str) -> bool:
    return path.replace("\\", "/").endswith(TARGET_FILE_SUFFIX)

def _parse_changed_locals(raw_line: str) -> dict[str, object]:
    marker = " locals="
    idx = raw_line.find(marker)
    if idx < 0:
        return {}
    raw_locals = raw_line[idx + len(marker):].strip()
    try:
        parsed = ast.literal_eval(raw_locals)
    except (SyntaxError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    decoded: dict[str, object] = {}
    for key, value in parsed.items():
        if isinstance(value, str):
            try:
                decoded[key] = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                decoded[key] = value
        else:
            decoded[key] = value
    return decoded

def extract_invariant(trace_text: str) -> dict[str, object]:
    frame_stack: list[dict[str, object]] = []
    observations: list[tuple[int, int]] = []
    relation_holds_for_all = True

    for raw_line in trace_text.splitlines():
        m = EVENT_RE.match(raw_line)
        if not m:
            continue
        if not _is_target_path(m.group("path")):
            continue
        if m.group("func") != TARGET_FUNC_QUAL:
            continue

        event = m.group("event")
        lineno = int(m.group("lineno"))

        if event == "call":
            frame_stack.append({})
            changed = _parse_changed_locals(raw_line)
            if changed:
                frame_stack[-1].update(changed)
            continue
        if event in ("return", "exception"):
            if frame_stack:
                changed = _parse_changed_locals(raw_line)
                if changed:
                    frame_stack[-1].update(changed)
                frame_stack.pop()
            continue
        if event != "line" or not frame_stack:
            continue

        changed = _parse_changed_locals(raw_line)
        if changed:
            frame_stack[-1].update(changed)

        if lineno != TARGET_LINE:
            continue

        snap = frame_stack[-1]
        m_v = snap.get("matches")
        mc_v = snap.get("max_contains")
        if not isinstance(m_v, int) or not isinstance(mc_v, int):
            continue
        observations.append((m_v, mc_v))
        if not (m_v < mc_v):
            relation_holds_for_all = False

    invariant_holds = bool(observations) and relation_holds_for_all
    return {
        "invariant_exists": invariant_holds,
        "observed_event_count": len(observations),
        "violating_pairs": [p for p in observations if not (p[0] < p[1])][:8],
        "sample_pairs": observations[:12],
    }

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
    extracted = extract_invariant(trace_text)

    qa = {
        "question_kind": "M7_Invariants",
        "question": (
            "Use the full test suite in `tests/qa/testcase.py`, class "
            "`TestContainsMatchesMaxContainsLoopInvariantSuiteQA` "
            "(21 tests). Each test invokes "
            "`cfnlint.jsonschema._keywords.contains` (file "
            "`src/cfnlint/jsonschema/_keywords.py`) with arrays and contains "
            "sub-schemas of varying shape against various `maxContains` and "
            "`minContains` configurations -- including overshoot runs (where "
            "the array contains more matching items than `maxContains`), "
            "no-overshoot runs (default `maxContains == len(instance)` or "
            "fewer matches than the bound), runs of dict / array / scalar "
            "sub-schemas, and runs that interleave matching with "
            "non-matching items. Inside `contains`, the loop "
            "`for each in instance:` (line `142`) reads `matches` (a counter "
            "incremented at line `144` only when "
            "`contains_validator.is_valid(each)`) and exits early via "
            "`yield + return` only when the post-increment check "
            "`matches > max_contains` (strict greater-than, line `145`) is "
            "True. Across the entire test-suite execution, consider every "
            "Python `line` event of `contains` whose `lineno == 142` (the "
            "for-loop header -- fired ONCE per iteration, immediately "
            "BEFORE each iteration's body executes). At every such event, "
            "is the candidate loop invariant `matches < max_contains` always "
            "held? Return JSON as `{\\\"invariant_exists\\\": <bool>}` where "
            "`true` means the invariant holds for every observed loop-header "
            "event and `false` means it does not."
        ),
        "template_answer": {
            "invariant_exists": "bool"
        },
        "oracle_answer": {
            "invariant_exists": bool(extracted["invariant_exists"]),
        },
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_file": TARGET_FILE_SUFFIX,
            "trace_events": ["line", "call", "return", "exception"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::"
                "TestContainsMatchesMaxContainsLoopInvariantSuiteQA"
            ),
            "target_lineno": TARGET_LINE,
            "observed_event_count": int(extracted["observed_event_count"]),
            "violating_pairs": list(extracted["violating_pairs"]),
            "sample_pairs": list(extracted["sample_pairs"]),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
