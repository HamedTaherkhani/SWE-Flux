#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


LINE_RE = re.compile(
    r"^(?P<path>[^:]+):(?P<lineno>\d+) (?P<func>\S+) event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

TARGET_SUFFIX = "yt_dlp/flux_bind.py"
# Py3.9: `yt_dlp.flux_bind.bind`. Py3.11+: may appear as `yt_dlp.flux_bind.FluxBind.bind`.
TARGET_FUNC_MARKERS = ("yt_dlp.flux_bind.bind", "yt_dlp.flux_bind.FluxBind.bind")


def _parse_locals_blob(blob: str) -> dict[str, str]:
    blob = blob.strip()
    if blob == "{}":
        return {}
    try:
        raw = ast.literal_eval(blob)
    except (ValueError, SyntaxError):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def _parse_int(raw: str) -> int | None:
    try:
        v = ast.literal_eval(raw.strip())
    except (ValueError, SyntaxError):
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return int(v)
    return None


def _locals_from_trace_row(raw_line: str) -> dict[str, str] | None:
    """Extract the trailing `locals={...}` blob from a trace row (line or return)."""
    line = raw_line.strip()
    if " locals=" not in line:
        return None
    blob = line.rsplit(" locals=", 1)[-1].strip()
    return _parse_locals_blob(blob)


def _is_target_bind_frame(path: str, func: str) -> bool:
    path = path.replace("\\", "/")
    if not path.endswith(TARGET_SUFFIX):
        return False
    return func in TARGET_FUNC_MARKERS or func.endswith(".FluxBind.bind")


def extract_invariant(trace_text: str) -> dict[str, object]:
    seen: set[int] = set()

    for m in LINE_RE.finditer(trace_text):
        path = m.group("path")
        func = m.group("func")
        if not _is_target_bind_frame(path, func):
            continue
        loc = _parse_locals_blob(m.group("locals"))
        if "m" not in loc:
            continue
        val = _parse_int(loc["m"])
        if val is not None:
            seen.add(val)

    # `line` events often log only *changed* locals (`{}` on many opcodes). `return`
    # rows with `TRACE_FULL_LOCALS_ON_RETURN=1` include full locals including `m`.
    for raw in trace_text.splitlines():
        s = raw.strip()
        if " event=return " not in s:
            continue
        if " locals=" not in s:
            continue
        # `/testbed/yt_dlp/flux_bind.py:42 yt_dlp.flux_bind.bind event=return retval=... locals={...}`
        try:
            pre, _ret = s.split(" event=return ", 1)
            last_sp = pre.rfind(" ")
            if last_sp == -1:
                continue
            func = pre[last_sp + 1 :]
            path_lineno = pre[:last_sp]
            colon = path_lineno.rfind(":")
            if colon == -1:
                continue
            path = path_lineno[:colon]
            _ = int(path_lineno[colon + 1 :])
        except ValueError:
            continue
        if not _is_target_bind_frame(path, func):
            continue
        loc = _locals_from_trace_row(s)
        if not loc or "m" not in loc:
            continue
        val = _parse_int(loc["m"])
        if val is not None:
            seen.add(val)

    if not seen:
        raise ValueError("No observations of local variable `m` in trace log.")

    if len(seen) == 1:
        v = next(iter(seen))
        return {"is_invariant": True, "invariant_value": v}

    return {"is_invariant": False, "invariant_value": None}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/flux_binding_invariant/trace.log",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/flux_bind.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/flux_binding_invariant/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    _ = Path(args.source).read_text(encoding="utf-8")

    out = extract_invariant(trace_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use `test/qa/flux_binding_invariant_test.py` and execute the full parametrized test suite "
            "in that file (all cases). Inside `yt_dlp/flux_bind.py`, method `FluxBind.bind`, consider "
            "the local variable `m`. In that method, `m` is assigned exactly once (a single "
            "`m = <integer literal>` statement) and is never reassigned afterward. "
            "Across all executions of `bind` in that suite, whenever `m` appears in the traced locals "
            "for `bind` (including `return` events when full locals are logged), is `m` an invariant "
            "integer (i.e. it always has the same value)? Answer with `is_invariant` (boolean) and "
            "`invariant_value` (that single integer if invariant, otherwise `null`)."
        ),
        "template_answer": {
            "is_invariant": "bool",
            "invariant_value": "int|null",
        },
        "oracle_answer": {
            "is_invariant": out["is_invariant"],
            "invariant_value": out["invariant_value"],
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
