from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT_DIR = Path("/testbed")
TARGET_FILE_SUFFIX = "cfnlint/jsonschema/_filter.py"
TARGET_FUNC_QUAL = (
    "cfnlint.jsonschema._filter.FunctionFilter._filter_schemas"
)
INSTANCE_ID = "filter_schemas_dual_dict_growth_loop_invariant_suite"
TARGET_LINE = 80

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

def _len_of_local(value: object) -> int | None:
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, str):
        s = value.strip()
        if not s.startswith("{") or not s.endswith("}"):
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
    pairs: list[tuple[int, int]] = []
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
        std_len = _len_of_local(snap.get("standard_schema"))
        grp_len = _len_of_local(snap.get("group_schema"))
        if std_len is None or grp_len is None:
            continue
        pairs.append((std_len, grp_len))
        if not (std_len >= grp_len):
            relation_holds_for_all = False

    invariant_holds = bool(pairs) and relation_holds_for_all
    return {
        "invariant_exists": invariant_holds,
        "observed_event_count": len(pairs),
        "violating_pairs": [p for p in pairs if not (p[0] >= p[1])][:8],
        "sample_pairs": pairs[:12],
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
            "`TestFilterSchemasDualDictGrowthLoopInvariantSuiteQA` "
            "(22 tests). Each test invokes "
            "`cfnlint.jsonschema._filter.FunctionFilter.filter` (which "
            "delegates to the private `_filter_schemas` method) on JSON "
            "schemas of varying composition -- standard-only, group-only, "
            "and mixed (with the group key first, last, and alternating); "
            "schemas with ``$ref`` (cfnLint short-circuit), schemas that "
            "exercise the post-loop ``object``/``patternProperties`` and "
            "``array``/``items`` arms, and one empty schema. Inside "
            "`_filter_schemas` (file `src/cfnlint/jsonschema/_filter.py`), "
            "two locally-declared dicts ``standard_schema`` and "
            "``group_schema`` are populated by the loop "
            "`for key, value in schema.items():` (line 80): each iteration "
            "appends to exactly one of the two dicts, depending on whether "
            "`key in self.group_functions`. Across the entire test-suite "
            "execution, consider every Python `line` event of "
            "`_filter_schemas` whose `lineno == 80` (the for-loop header, "
            "fired once per iteration immediately BEFORE the body runs). At "
            "every such event, is the candidate loop invariant "
            "`len(standard_schema) >= len(group_schema)` always held? "
            "Return JSON as `{\\\"invariant_exists\\\": <bool>}` where "
            "`true` means the invariant holds at every observed event and "
            "`false` means it does not."
        ),
        "template_answer": {"invariant_exists": "bool"},
        "oracle_answer": {"invariant_exists": bool(extracted["invariant_exists"])},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_file": TARGET_FILE_SUFFIX,
            "trace_events": ["line", "call", "return", "exception"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::"
                "TestFilterSchemasDualDictGrowthLoopInvariantSuiteQA"
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
