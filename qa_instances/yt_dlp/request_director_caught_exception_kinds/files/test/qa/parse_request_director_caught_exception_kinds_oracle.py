#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

EXC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=exception exc=(?P<exc>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _send_bounds_and_handlers(source_text: str) -> tuple[int, int, set[str]]:
    tree = ast.parse(source_text)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "RequestDirector":
            for fn in node.body:
                if isinstance(fn, ast.FunctionDef) and fn.name == "send":
                    caught: set[str] = set()
                    for child in ast.walk(fn):
                        if isinstance(child, ast.ExceptHandler):
                            if child.type is None:
                                continue
                            if isinstance(child.type, ast.Name):
                                caught.add(child.type.id)
                            elif isinstance(child.type, ast.Tuple):
                                for elt in child.type.elts:
                                    if isinstance(elt, ast.Name):
                                        caught.add(elt.id)
                    return fn.lineno, fn.end_lineno or fn.lineno, caught
    raise ValueError("RequestDirector.send not found in source.")


def _exception_kind(exc_field: str) -> str:
    text = exc_field.strip()
    if ":" in text:
        return text.split(":", 1)[0].strip()
    return text.strip() or "Exception"


def extract_caught_exception_kinds(trace_text: str, source_text: str) -> dict[str, object]:
    start, end, caught_types = _send_bounds_and_handlers(source_text)
    has_generic = "Exception" in caught_types
    observed: list[str] = []

    for m in EXC_RE.finditer(trace_text):
        # In this runtime, method traces are reported as module-qualified function names
        # (e.g. `yt_dlp.networking.common.send`) without class qualification.
        if not m.group("func").endswith(".send"):
            continue
        lineno = int(m.group("lineno"))
        if not (start <= lineno <= end):
            continue

        kind = _exception_kind(m.group("exc"))
        if kind == "NoSupportingHandlers":
            # This one is raised at the end of send(), not caught in send().
            continue
        if kind in caught_types or has_generic:
            observed.append(kind)

    kinds = sorted(set(observed))
    if not kinds:
        raise ValueError("No caught exception kinds observed inside RequestDirector.send.")

    return {"caught_exception_kinds": kinds}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/request_director_caught_exception_kinds/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/yt_dlp/networking/common.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/request_director_caught_exception_kinds/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    answer = extract_caught_exception_kinds(trace_text, source_text)

    qa = {
        "question_kind": "abnormal_behavior_prediction",
        "question": (
            "Use `test/qa/request_director_caught_exception_kinds_test.py`, class "
            "`TestRequestDirectorCaughtExceptionKindsQA`, method "
            "`test_request_director_caught_exception_kinds_case`. In "
            "`yt_dlp/networking/common.py::RequestDirector.send`, which exception kinds are "
            "caught by the method's internal `except` blocks during this execution? Return them "
            "as `caught_exception_kinds`."
        ),
        "template_answer": {
            "caught_exception_kinds": ["str"],
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
