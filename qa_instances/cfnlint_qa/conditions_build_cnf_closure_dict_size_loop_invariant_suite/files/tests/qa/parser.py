from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT_DIR = Path("/testbed")
TARGET_FILE_SUFFIX = "cfnlint/conditions/conditions.py"
TARGET_FUNC_QUAL = (
    "cfnlint.conditions.conditions.Conditions._build_cnf.<locals>._build_equal_vars"
)
INSTANCE_ID = "conditions_build_cnf_closure_dict_size_loop_invariant_suite"
TARGET_LINE = 139

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>\w+) ",
)

KEY_HASH_RE = re.compile(r"'([0-9a-f]{40})':")

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

def _len_from_repr(value: object) -> int | None:
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, str):
        return len(set(KEY_HASH_RE.findall(value)))
    return None

def extract_invariant(trace_text: str) -> dict[str, object]:
    frame_state: dict[int, dict[str, object]] = {}
    relation_holds_for_all = True
    observed_events = 0
    observed_pairs: list[tuple[int, int]] = []

    frame_stack: list[dict[str, object]] = []

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

        snapshot = frame_stack[-1]
        ev_len = _len_from_repr(snapshot.get("equal_vars"))
        eq_len = _len_from_repr(snapshot.get("equals"))
        if ev_len is None or eq_len is None:
            continue

        observed_events += 1
        observed_pairs.append((ev_len, eq_len))
        if ev_len != eq_len:
            relation_holds_for_all = False

    invariant_holds = bool(observed_events) and relation_holds_for_all
    return {
        "invariant_exists": invariant_holds,
        "observed_event_count": observed_events,
        "sample_pairs": observed_pairs[:8],
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
        "question_kind": "invariant_properties",
        "question": (
            "Use the full test suite in `tests/qa/testcase.py`, class "
            "`TestConditionsBuildCnfClosureDictSizeLoopInvariantSuiteQA` "
            "(23 tests). Each test instantiates "
            "`cfnlint.conditions.conditions.Conditions(cfn)` against a "
            "different shape of CloudFormation template -- parameter-"
            "comparison Conditions, static-True/static-False Conditions, "
            "multiple Conditions sharing a parameter, duplicate-hash "
            "Conditions that exercise the early `continue` branch, "
            "Conditions composed via `Fn::And` / `Fn::Or` / `Fn::Not` and "
            "named-condition references (`Condition: Name`), Conditions "
            "comparing pseudo Refs (`AWS::Region`, `AWS::Partition`), "
            "Conditions with single- and multi-assertion Rules (including a "
            "rules-only template), Conditions whose parameters carry "
            "`AllowedValues` driving iteration 2 of `_build_cnf`, and "
            "high-volume mixes that exercise all of the above in a single "
            "template. `Conditions.__init__` calls `_build_cnf`, which "
            "defines an inner closure `_build_equal_vars(c_equals)` (qualname "
            "`cfnlint.conditions.conditions.Conditions._build_cnf.<locals>._build_equal_vars`) "
            "that mutates two enclosing-scope dicts: `equal_vars` and "
            "`equals`. Within `for c_equal in c_equals:`, an entry is added "
            "to `equal_vars` at one of lines 124/126/128 (depending on "
            "`c_equal.is_static`) and an entry is added to `equals` at line "
            "139. Across the entire test-suite execution, consider every "
            "Python `line` event of the inner closure whose `lineno == 139` "
            "(i.e., the moment immediately BEFORE the `equals[c_equal.hash] "
            "= c_equal` statement is executed). At every such event, is the "
            "loop invariant `len(equal_vars) == len(equals)` always held? "
            "Return JSON as `{\\\"invariant_exists\\\": <bool>}` where `true` "
            "means the invariant holds at every observed event and `false` "
            "means it does not."
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
                "TestConditionsBuildCnfClosureDictSizeLoopInvariantSuiteQA"
            ),
            "target_lineno": TARGET_LINE,
            "observed_event_count": int(extracted["observed_event_count"]),
            "sample_pairs": list(extracted["sample_pairs"]),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
