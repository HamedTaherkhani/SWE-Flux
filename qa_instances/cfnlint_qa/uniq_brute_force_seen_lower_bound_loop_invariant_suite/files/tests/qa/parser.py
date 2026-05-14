from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT_DIR = Path("/testbed")
TARGET_FILE_SUFFIX = "cfnlint/jsonschema/_utils.py"
TARGET_FUNC_QUAL = "cfnlint.jsonschema._utils.uniq"
INSTANCE_ID = "uniq_brute_force_seen_lower_bound_loop_invariant_suite"
TARGET_LINE = 140

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
    for k, v in parsed.items():
        if isinstance(v, str):
            try:
                decoded[k] = ast.literal_eval(v)
            except (SyntaxError, ValueError):
                decoded[k] = v
        else:
            decoded[k] = v
    return decoded

def _len_of_list_local(value: object) -> int | None:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, str):
        s = value.strip()
        if not s.startswith("[") or not s.endswith("]"):
            return None
        inner = s[1:-1].strip()
        if not inner:
            return 0
        depth = 0
        commas = 0
        in_str: str | None = None
        i = 0
        while i < len(inner):
            ch = inner[i]
            if in_str is not None:
                if ch == "\\" and i + 1 < len(inner):
                    i += 2
                    continue
                if ch == in_str:
                    in_str = None
            else:
                if ch in ("'", '"'):
                    in_str = ch
                elif ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    depth -= 1
                elif ch == "," and depth == 0:
                    commas += 1
            i += 1
        return commas + 1
    return None

def extract_invariant(trace_text: str) -> dict[str, object]:
    frame_stack: list[dict[str, object]] = []
    observations: list[int] = []
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
        if event == "return":
            if frame_stack:
                changed = _parse_changed_locals(raw_line)
                if changed:
                    frame_stack[-1].update(changed)
                frame_stack.pop()
            continue
        if event == "exception":
            if frame_stack:
                changed = _parse_changed_locals(raw_line)
                if changed:
                    frame_stack[-1].update(changed)
            continue
        if event != "line" or not frame_stack:
            continue

        changed = _parse_changed_locals(raw_line)
        if changed:
            frame_stack[-1].update(changed)

        if lineno != TARGET_LINE:
            continue

        snap = frame_stack[-1]
        seen_len = _len_of_list_local(snap.get("seen"))
        if seen_len is None:
            continue
        observations.append(seen_len)
        if not (seen_len > 0):
            relation_holds_for_all = False

    invariant_holds = bool(observations) and relation_holds_for_all
    return {
        "invariant_exists": invariant_holds,
        "observed_event_count": len(observations),
        "violating_count": sum(1 for s in observations if not (s > 0)),
        "first_samples": observations[:24],
        "min_observed": min(observations) if observations else None,
        "max_observed": max(observations) if observations else None,
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
            "`TestUniqBruteForceSeenLowerBoundLoopInvariantSuiteQA` "
            "(21 tests). Each test calls "
            "`cfnlint.jsonschema._utils.uniq(container)` (file "
            "`src/cfnlint/jsonschema/_utils.py`) on containers whose "
            "heterogeneous types force the function into its brute-force "
            "fallback (the ``except (NotImplementedError, TypeError):`` arm "
            "at line 138). Inside the fallback, the function initialises "
            "``seen = []`` (line 139) and iterates ``for e in c:`` (line "
            "140), where the inner ``for i in seen:`` loop walks all "
            "previously appended items and ``seen.append(e)`` (line 146) "
            "extends the list. Across the entire test-suite execution, "
            "consider every Python `line` event of `uniq` whose "
            "`lineno == 140` (the outer for-loop header, fired once per "
            "iteration immediately BEFORE that iteration's body runs and "
            "once after the loop completes). At every such event, is the "
            "candidate loop invariant `len(seen) > 0` always held? Return "
            "JSON as `{\\\"invariant_exists\\\": <bool>}` where `true` "
            "means the invariant holds at every observed event and `false` "
            "means it does not."
        ),
        "template_answer": {"invariant_exists": "bool"},
        "oracle_answer": {"invariant_exists": bool(extracted["invariant_exists"])},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_file": TARGET_FILE_SUFFIX,
            "trace_events": ["line", "call", "return", "exception"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::"
                "TestUniqBruteForceSeenLowerBoundLoopInvariantSuiteQA"
            ),
            "target_lineno": TARGET_LINE,
            "observed_event_count": int(extracted["observed_event_count"]),
            "violating_count": int(extracted["violating_count"]),
            "first_samples": list(extracted["first_samples"]),
            "min_observed": extracted["min_observed"],
            "max_observed": extracted["max_observed"],
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
