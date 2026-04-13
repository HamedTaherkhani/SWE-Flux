#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

EXC_RE = re.compile(
    r"(?m)(?:^\d{4}-\d{2}-\d{2} .+? )?"
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=exception exc=(?P<exc>.*?) locals=(?P<locals>\{.*\})$",
)


def _absorb_chain_bounds_and_handlers(source_text: str) -> tuple[int, int, set[str]]:
    tree = ast.parse(source_text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "absorb_chain":
            caught: set[str] = set()
            for child in ast.walk(node):
                if isinstance(child, ast.ExceptHandler):
                    if child.type is None:
                        continue
                    if isinstance(child.type, ast.Name):
                        caught.add(child.type.id)
                    elif isinstance(child.type, ast.Tuple):
                        for elt in child.type.elts:
                            if isinstance(elt, ast.Name):
                                caught.add(elt.id)
            start = node.lineno
            end = start
            for n in ast.walk(node):
                el = getattr(n, "end_lineno", None)
                if isinstance(el, int):
                    end = max(end, el)
            return start, end, caught
    raise ValueError("absorb_chain not found in source.")


def _exception_kind(exc_field: str) -> str:
    text = exc_field.strip()
    if ":" in text:
        return text.split(":", 1)[0].strip()
    return text.strip() or "Exception"


def extract_caught_exception_kinds(trace_text: str, source_text: str) -> dict[str, object]:
    start, end, caught_types = _absorb_chain_bounds_and_handlers(source_text)
    has_generic = "Exception" in caught_types or "BaseException" in caught_types
    observed: list[str] = []

    for m in EXC_RE.finditer(trace_text):
        func = m.group("func")
        if func != "yt_dlp.fault_relay.absorb_chain" and not func.endswith(".absorb_chain"):
            continue
        lineno = int(m.group("lineno"))
        if not (start <= lineno <= end):
            continue
        kind = _exception_kind(m.group("exc"))
        if kind in caught_types or has_generic:
            observed.append(kind)

    kinds = sorted(set(observed))
    if not kinds:
        raise ValueError("No caught exception kinds observed inside absorb_chain.")

    return {"caught_exception_kinds": kinds}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/fault_relay_caught_kinds/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/yt_dlp/fault_relay.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/fault_relay_caught_kinds/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    answer = extract_caught_exception_kinds(trace_text, source_text)

    qa = {
        "question_kind": "abnormal_behavior_prediction",
        "question": (
            "Use `test/qa/fault_relay_caught_kinds_test.py`, class `TestFaultRelayCaughtKindsQA`, method "
            "`test_fault_relay_caught_kinds_case`. In `yt_dlp/fault_relay.py::absorb_chain`, which exception "
            "kinds are caught by that function's internal `except` blocks during this test run? Return them "
            "as `caught_exception_kinds`, sorted ascending lexicographically by exception name (the Python "
            "class name as a string, e.g. `ValueError`)."
        ),
        "template_answer": {
            "caught_exception_kinds": ["str"],
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
