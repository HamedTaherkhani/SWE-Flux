from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT_DIR = Path("/testbed")
TARGET_FILE_SUFFIX = "cfnlint/template/template.py"
TARGET_FUNC_QUAL = "cfnlint.template.template.Template._search_deep_keys"
INSTANCE_ID = "template_search_deep_keys_chronological_monotonicity_suite"

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

def _classify_monotonicity(seq: list[int]) -> str:
    if len(seq) < 2:
        return "None"
    has_pos = False
    has_neg = False
    has_zero = False
    for a, b in zip(seq, seq[1:]):
        d = b - a
        if d > 0:
            has_pos = True
        elif d < 0:
            has_neg = True
        else:
            has_zero = True
    if has_pos and has_neg:
        return "None"
    if has_pos and not has_zero and not has_neg:
        return "Strictly Increasing"
    if has_neg and not has_zero and not has_pos:
        return "Strictly Decreasing"
    if has_pos and not has_neg:
        return "Non-Decreasing"
    if has_neg and not has_pos:
        return "Non-Increasing"
    return "Non-Decreasing"

def extract_monotonicity(trace_text: str) -> dict[str, object]:
    frame_stack: list[dict[str, object]] = []
    series: list[int] = []
    frame_count = 0

    for raw_line in trace_text.splitlines():
        m = EVENT_RE.match(raw_line)
        if not m:
            continue
        if not _is_target_path(m.group("path")):
            continue
        if m.group("func") != TARGET_FUNC_QUAL:
            continue

        event = m.group("event")

        if event == "call":
            frame_stack.append({})
            frame_count += 1
            changed = _parse_changed_locals(raw_line)
            if changed:
                frame_stack[-1].update(changed)
            continue
        if event in ("return", "exception"):
            if frame_stack:
                changed = _parse_changed_locals(raw_line)
                if changed:
                    frame_stack[-1].update(changed)
                ln = _len_of_local(frame_stack[-1].get("keys"))
                if ln is not None:
                    series.append(ln)
                frame_stack.pop()
            continue
        if event != "line" or not frame_stack:
            continue

        changed = _parse_changed_locals(raw_line)
        if changed:
            frame_stack[-1].update(changed)
        ln = _len_of_local(frame_stack[-1].get("keys"))
        if ln is not None:
            series.append(ln)

    return {
        "monotonicity": _classify_monotonicity(series),
        "observed_event_count": len(series),
        "observed_frame_count": frame_count,
        "first_samples": series[:30],
        "min_observed": min(series) if series else None,
        "max_observed": max(series) if series else None,
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
    extracted = extract_monotonicity(trace_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the full test suite in `tests/qa/testcase.py`, class "
            "`TestTemplateSearchDeepKeysChronologicalMonotonicitySuiteQA` "
            "(20 tests). Each test invokes "
            "`cfnlint.template.template.Template.search_deep_keys` (which "
            "delegates to the recursive private method "
            "`Template._search_deep_keys`) on templates of varying shape -- "
            "flat resources, deeply nested dicts, mixed dict/list trees, "
            "wide breadth at a single level, multiple top-level sections "
            "(`Parameters`/`Conditions`/`Resources`/`Outputs`), regex search "
            "patterns, the `includeGlobals=True` arm, lists at the root, and "
            "high-volume runs across many resources. Inside "
            "`_search_deep_keys` (file `src/cfnlint/template/template.py`), "
            "each frame allocates a fresh local list `keys = []` (line 362) "
            "and grows it via `keys.append(pathprop)` and "
            "`keys.extend(self._search_deep_keys(...))` from the return value "
            "of recursive calls -- so within a single frame `len(keys)` is "
            "non-decreasing. Sample two locals at every Python `line` event "
            "of `_search_deep_keys` across the entire test run, in "
            "chronological order across ALL frames: the freshly-allocated "
            "result list `keys` (observed via its length) and the input "
            "parameter `path` (observed via its length). Considering the "
            "resulting `len(keys)` sequence in chronological order across "
            "ALL frames, what is its monotonic relationship? Return JSON as "
            "`{\\\"monotonicity\\\": <label>}` where `<label>` is one of "
            "`\\\"Strictly Increasing\\\"`, `\\\"Strictly Decreasing\\\"`, "
            "`\\\"Non-Decreasing\\\"`, `\\\"Non-Increasing\\\"`, or "
            "`\\\"None\\\"`."
        ),
        "template_answer": {"monotonicity": "str"},
        "oracle_answer": {"monotonicity": str(extracted["monotonicity"])},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_file": TARGET_FILE_SUFFIX,
            "trace_events": ["line", "call", "return", "exception"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::"
                "TestTemplateSearchDeepKeysChronologicalMonotonicitySuiteQA"
            ),
            "observed_event_count": int(extracted["observed_event_count"]),
            "observed_frame_count": int(extracted["observed_frame_count"]),
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
