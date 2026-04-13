#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


CALL_RE = re.compile(
    r"^(?P<path>[^:]+):(?P<lineno>\d+) (?P<func>\S+) event=call locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

TARGET_SUFFIX = "yt_dlp/ledger_walk.py"
TARGET_FUNCS = {"yt_dlp.ledger_walk.ledger_walk"}


def _parse_locals_blob(blob: str) -> dict[str, str]:
    blob = blob.strip()
    if blob == "{}":
        return {}
    try:
        raw = ast.literal_eval(blob)
    except (ValueError, SyntaxError):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def _parse_str(raw: str) -> str | None:
    try:
        v = ast.literal_eval(raw.strip())
    except (ValueError, SyntaxError):
        return None
    if isinstance(v, str):
        return v
    return None


def prefix_loop_invariant_holds(token: str) -> bool:
    """
    Check the standard prefix-sum invariant for:

        checksum = 0
        for i, ch in enumerate(token):
            checksum = (checksum + ord(ch)) % 256

    At the start of each iteration i (immediately before the assignment to `checksum`),
    we require:
        checksum == (sum_{j=0}^{i-1} ord(token[j])) mod 256
    (empty sum is 0 when i == 0).
    """
    checksum = 0
    for i, ch in enumerate(token):
        expected = sum(ord(token[j]) for j in range(i)) % 256
        if checksum != expected:
            return False
        checksum = (checksum + ord(ch)) % 256
    return True


def extract_loop_invariant_holds(trace_text: str) -> bool:
    ok = True
    found = 0
    for m in CALL_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        if not path.endswith(TARGET_SUFFIX):
            continue
        func = m.group("func")
        if func not in TARGET_FUNCS and not func.endswith(".ledger_walk"):
            continue
        loc = _parse_locals_blob(m.group("locals"))
        if "token" not in loc:
            continue
        token = _parse_str(loc["token"])
        if token is None:
            continue
        found += 1
        ok = ok and prefix_loop_invariant_holds(token)

    if found == 0:
        raise ValueError("No call events captured for yt_dlp.ledger_walk.ledger_walk with token=...")

    return ok


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/ledger_loop_invariant_probe/trace.log",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/ledger_walk.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/ledger_loop_invariant_probe/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    _ = Path(args.source).read_text(encoding="utf-8")

    holds = extract_loop_invariant_holds(trace_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use `test/qa/ledger_loop_invariant_probe_test.py` and execute the full parametrized test suite "
            "in that file (all cases). Inside `yt_dlp/ledger_walk.py`, function `ledger_walk`, consider "
            "the `for i, ch in enumerate(token):` loop and its local variable `checksum`. "
            "At the start of each loop iteration `i` (immediately before executing the assignment "
            "`checksum = (checksum + ord(ch)) % 256`), must it always be true that "
            "`checksum == (sum(ord(token[j]) for j in range(i)) % 256)` (with the empty sum defined as `0` "
            "when `i == 0`)? Answer as `loop_invariant_holds` (boolean): `true` only if this predicate "
            "holds at the start of every iteration for every call to `ledger_walk` in the suite."
        ),
        "template_answer": {
            "loop_invariant_holds": "bool",
        },
        "oracle_answer": {
            "loop_invariant_holds": holds,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
