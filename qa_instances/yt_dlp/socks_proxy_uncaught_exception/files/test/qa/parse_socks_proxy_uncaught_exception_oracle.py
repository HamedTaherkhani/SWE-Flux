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


def _extract_message(exc_kind: str, exc_repr: str) -> str:
    text = exc_repr.strip()
    if text.startswith(f"{exc_kind}("):
        try:
            node = ast.parse(text, mode="eval").body
            if isinstance(node, ast.Call) and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    return first.value
        except Exception:
            pass

    if (text.startswith("'") and text.endswith("'")) or (
        text.startswith('"') and text.endswith('"')
    ):
        try:
            val = ast.literal_eval(text)
            if isinstance(val, str):
                return val
        except Exception:
            pass

    return text


def extract_exception(trace_text: str) -> dict[str, str]:
    for m in EXC_RE.finditer(trace_text):
        func = m.group("func")
        if not func.endswith(".make_socks_proxy_opts"):
            continue

        exc_field = m.group("exc").strip()
        if ":" in exc_field:
            exc_kind, exc_repr = exc_field.split(":", 1)
            exc_kind = exc_kind.strip()
            exc_repr = exc_repr.strip()
        else:
            exc_kind = "Exception"
            exc_repr = exc_field

        return {
            "exception_kind": exc_kind,
            "exception_message": _extract_message(exc_kind, exc_repr),
        }

    raise ValueError("Could not capture uncaught exception from make_socks_proxy_opts.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/socks_proxy_uncaught_exception/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/socks_proxy_uncaught_exception/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    answer = extract_exception(trace_text)

    qa = {
        "question_kind": "abnormal_behavior_prediction",
        "question": (
            "Use `test/qa/socks_proxy_uncaught_exception_test.py`, class "
            "`TestSocksProxyUncaughtExceptionQA`, method "
            "`test_socks_proxy_uncaught_exception_case`. Inside "
            "`yt_dlp/networking/_helper.py::make_socks_proxy_opts`, when the call "
            "`make_socks_proxy_opts(\"socks://127.0.0.1\")` reaches its uncaught exception "
            "event, what are the exact `exception_kind` and `exception_message`?"
        ),
        "template_answer": {
            "exception_kind": "str",
            "exception_message": "str",
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
