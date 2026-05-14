#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


# Trace plugin records the function as `yt_dlp.cookies._get_linux_desktop_environment`
# (mod=yt_dlp.cookies, co_name=_get_linux_desktop_environment on Python 3.9 -- no
# class wrapper).
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/cookies\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.cookies\._get_linux_desktop_environment) "
    r"event=line locals=\{.*\}$",
    re.MULTILINE,
)


def extract_path(trace_text: str) -> dict:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError(
            "No line events for _get_linux_desktop_environment in trace.")

    executed_path = []
    for m in matches:
        executed_path.append({
            "file": "yt_dlp/cookies.py",
            "func": "_get_linux_desktop_environment",
            "line": int(m.group("lineno")),
        })
    return {"executed_path": executed_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/linux_desktop_environment_execution_path/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/linux_desktop_environment_execution_path/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_path(trace_text)

    qa = {
        "question_kind": "C2_InterProceduralCFG",
        "question": (
            "Use `test/qa/linux_desktop_environment_execution_path_test.py`, class "
            "`TestLinuxDesktopEnvironmentExecutionPathQA`, method "
            "`test_linux_desktop_environment_execution_path_case`. "
            "The test calls "
            "`yt_dlp.cookies._get_linux_desktop_environment(ENV, _StubLogger())` "
            "(defined at lines 761-829 in `yt_dlp/cookies.py`) with the exact `ENV` dict "
            "literal at the top of the test file: "
            "`{'XDG_CURRENT_DESKTOP': 'Cinnamon:KDE', 'KDE_SESSION_VERSION': '99', "
            "'DESKTOP_SESSION': 'deepin'}`. "
            "The body is a long if/elif chain that first dispatches on "
            "`XDG_CURRENT_DESKTOP` (split by `':'` and stripped, iterated as `part`), "
            "then on `DESKTOP_SESSION`, then on a final fallback. The KDE branch at line "
            "781 reads `KDE_SESSION_VERSION` and dispatches on its string value with a "
            "fallback `else` arm. Note: Python emits a line event for *each* `elif` "
            "predicate that is evaluated (whether true or false), and the FOR statement "
            "at line 769 fires once before the first iteration plus once after each "
            "iteration's body completes. `else:` keywords (at lines such as 789) do NOT "
            "emit line events; only their body lines do. The `'Cinnamon'` token is NOT "
            "the same as `'X-Cinnamon'`. "
            "Report the EXACT ordered sequence of executed lines inside this function "
            "during this test run, INCLUDING repeats. Return a JSON object with one key "
            "`executed_path` whose value is a list of objects each shaped exactly as "
            "`{\"file\": \"yt_dlp/cookies.py\", \"func\": "
            "\"_get_linux_desktop_environment\", \"line\": <int>}`, in the order Python's "
            "line-trace events fired."
        ),
        "template_answer": {
            "executed_path": [
                {
                    "file": "str",
                    "func": "str",
                    "line": "int",
                },
            ],
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
