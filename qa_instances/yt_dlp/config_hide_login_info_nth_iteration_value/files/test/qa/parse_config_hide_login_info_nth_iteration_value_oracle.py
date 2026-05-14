#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin emits per-line `event=line` for `hide_login_info`. The
# `locals=...` block carries only changed locals since the prior event, so we
# walk events in order and accumulate. The for-loop body's first executable
# line is line 4974 (`if opt in PRIVATE_OPTS and idx + 1 < len(opts):`); each
# iteration begins by emitting that event with `idx`/`opt`/`opts` already
# bound to that iteration's values.
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.hide_login_info) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


TARGET_BODY_LINE = "4974"
TARGET_ITERATION = 8  # 1-indexed


def extract_iteration_snapshot(trace_text: str) -> dict:
    cumulative: dict[str, str] = {}
    snapshots: list[dict[str, str]] = []

    for m in LINE_RE.finditer(trace_text):
        delta = ast.literal_eval(m.group("locals"))
        cumulative.update(delta)
        if m.group("lineno") == TARGET_BODY_LINE:
            snapshots.append(dict(cumulative))

    if len(snapshots) < TARGET_ITERATION:
        raise ValueError(
            f"Need at least {TARGET_ITERATION} body-line events, "
            f"got {len(snapshots)}.")

    snap = snapshots[TARGET_ITERATION - 1]
    for key in ("idx", "opt", "opts"):
        if key not in snap:
            raise ValueError(f"`{key}` not in snapshot for iteration {TARGET_ITERATION}")

    return {
        "idx": ast.literal_eval(snap["idx"]),
        "opt": ast.literal_eval(snap["opt"]),
        "opts": ast.literal_eval(snap["opts"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/config_hide_login_info_nth_iteration_value/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/config_hide_login_info_nth_iteration_value/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_iteration_snapshot(trace_text)

    qa = {
        "question_kind": "C3_Loops",
        "question": (
            "Use `test/qa/config_hide_login_info_nth_iteration_value_test.py`, class "
            "`TestConfigHideLoginInfoNthIterationValueQA`, method "
            "`test_config_hide_login_info_nth_iteration_value_case`. "
            "The test calls `Config.hide_login_info(OPTS)` -- the static method "
            "`hide_login_info` of class `Config` defined in `yt_dlp/utils/_utils.py` at "
            "line 4961 -- with the exact `OPTS` list literal at the top of the test file: "
            "`['-u', 'myuser', '--password', 'mypass', '--video-password=secret', "
            "'extra1', '--username', 'someone', 'extra2']`. "
            "Inside `hide_login_info`, line 4972 first reassigns `opts = list(map("
            "_scrub_eq, opts))` (this transforms any `--option=value` form into "
            "`--option=PRIVATE` for the seven keys in `PRIVATE_OPTS`; separated "
            "`--option value` pairs are NOT touched by `_scrub_eq`). Then the for-loop at "
            "line 4973 does `for idx, opt in enumerate(opts):` with body starting at "
            "line 4974. Inside the body, `if opt in PRIVATE_OPTS and idx + 1 < len(opts):` "
            "MUTATES `opts[idx + 1] = 'PRIVATE'` -- so on later iterations the loop "
            "variable `opt` may be bound to a value that was placed there by a PRIOR "
            "iteration's mutation, NOT to the value that was at that index at function "
            "entry. "
            "Report the exact state at the START of the **8th iteration** (1-indexed -- "
            "i.e., the moment the body's first line at 4974 fires for the 8th time, after "
            "iterations 1-7 have completed). Return a JSON object with three keys: "
            "`idx` (int, the loop variable `idx` at that moment), `opt` (str, the loop "
            "variable `opt` at that moment), and `opts` (list[str], the exact contents of "
            "the `opts` local list at that moment, including any element that has already "
            "been replaced with `'PRIVATE'` by an earlier iteration)."
        ),
        "template_answer": {
            "idx": "int",
            "opt": "str",
            "opts": ["str"],
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
