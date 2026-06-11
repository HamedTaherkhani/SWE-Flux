from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT_DIR = Path("/testbed")
TARGET_FILE_SUFFIX = "cfnlint/schema/resolver/_resolver.py"
TARGET_FUNC_QUAL = "cfnlint.schema.resolver._resolver.RefResolver._walk_cfn_pointer"
INSTANCE_ID = "resolver_walk_cfn_pointer_pointer_temporal_value_history"

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>\w+) ",
    re.MULTILINE,
)

POINTER_IN_LOCALS_RE = re.compile(r"'pointer':\s*(['\"])(?P<inner>.*?)\1")

def _is_target_path(path: str) -> bool:
    p = path.replace("\\", "/")
    return p.endswith(TARGET_FILE_SUFFIX)

def _parse_pointer_from_locals_suffix(locals_suffix: str) -> list[str] | None:
    m = POINTER_IN_LOCALS_RE.search(locals_suffix)
    if not m:
        return None
    raw = m.group("inner")
    try:
        val = ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return None
    if not isinstance(val, list):
        return None
    return [str(x) for x in val]

def extract_pointer_snapshot_history(trace_text: str) -> list[list[str]]:
    history: list[list[str]] = []
    for m in TRACE_RE.finditer(trace_text):
        if m.group("event") != "call":
            continue
        if not _is_target_path(m.group("path")) or m.group("func") != TARGET_FUNC_QUAL:
            continue
        line_start = m.end()
        nl = trace_text.find("\n", line_start)
        rest = trace_text[line_start:] if nl == -1 else trace_text[line_start:nl]
        if "locals=" not in rest:
            continue
        _, _, locals_part = rest.partition("locals=")
        snap = _parse_pointer_from_locals_suffix(locals_part)
        if snap is not None:
            history.append(snap)
    return history

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
    history = extract_pointer_snapshot_history(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestResolverWalkCfnPointerPointerTemporalHistoryQA`, method "
            "`test_resolver_walk_cfn_pointer_pointer_temporal_value_history_case`. "
            "Focus only on method `cfnlint.schema.resolver._resolver.RefResolver._walk_cfn_pointer` "
            "in file `src/cfnlint/schema/resolver/_resolver.py`. "
            "Some `resolve_cfn_pointer` inputs are satisfied without ever calling `_walk_cfn_pointer`; "
            "those must not appear in your answer. "
            "Consider the formal parameter `pointer` (path segments derived from the CFN pointer "
            "string, after `resolve_cfn_pointer` strips its first slash-separated token). "
            "At every **call** to `_walk_cfn_pointer`, Python binds a fresh list value to `pointer`. "
            "What is the ordered sequence of **all** such list values across the entire test run, "
            "chronological order (earliest call first), including empty lists? "
            "Return the answer as `pointer_snapshot_history`: a JSON array; each element is a JSON "
            "array of segment strings (use the exact segment text, e.g. `*` for wildcards). "
            "Do not deduplicate: if the tracer shows N calls with bound `pointer` values, the answer "
            "must have length N."
        ),
        "template_answer": {
            "pointer_snapshot_history": [
                ["str", "str"],
                [],
            ]
        },
        "oracle_answer": {
            "pointer_snapshot_history": history,
        },
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["call"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestResolverWalkCfnPointerPointerTemporalHistoryQA::"
                "test_resolver_walk_cfn_pointer_pointer_temporal_value_history_case"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
