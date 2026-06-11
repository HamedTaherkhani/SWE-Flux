#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin emits line events for `__contains__`. We want the moment the
# return-expression at line 43 is evaluated. Walk events in order, accumulate
# diff-style locals, snapshot at the line-43 event.
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/networking/impersonate\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.networking\.impersonate\.__contains__) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


TARGET_LINE = "43"

# Dataclass repr is `ImpersonateTarget(client=X, version=Y, os=Z, os_version=W)`
# where each value is either `'<str>'` or `None`. Extract via regex per field.
TARGET_REPR_RE = re.compile(
    r"ImpersonateTarget\("
    r"client=(?P<client>'[^']*'|None), "
    r"version=(?P<version>'[^']*'|None), "
    r"os=(?P<os>'[^']*'|None), "
    r"os_version=(?P<os_version>'[^']*'|None)\)"
)


def _parse_target(repr_text: str) -> dict:
    # The locals dict already stores each value as a *string* (the original
    # `repr()`), so `repr_text` is already
    # "ImpersonateTarget(client='chrome', ...)". No outer-quote decoding needed.
    m = TARGET_REPR_RE.fullmatch(repr_text)
    if not m:
        raise ValueError(f"Could not parse ImpersonateTarget repr: {repr_text!r}")
    return {
        field: ast.literal_eval(m.group(field))
        for field in ("client", "version", "os", "os_version")
    }


def extract_snapshot(trace_text: str) -> dict:
    cumulative: dict[str, str] = {}
    snapshot_at_target: dict[str, str] | None = None

    for m in LINE_RE.finditer(trace_text):
        delta = ast.literal_eval(m.group("locals"))
        cumulative.update(delta)
        if m.group("lineno") == TARGET_LINE:
            snapshot_at_target = dict(cumulative)
            break

    if snapshot_at_target is None:
        raise ValueError(f"No line-{TARGET_LINE} event for __contains__ found.")

    if "self" not in snapshot_at_target or "target" not in snapshot_at_target:
        raise ValueError(
            f"Locals at line {TARGET_LINE} missing self/target: {snapshot_at_target!r}")

    self_fields = _parse_target(snapshot_at_target["self"])
    target_fields = _parse_target(snapshot_at_target["target"])

    return {
        "self_client": self_fields["client"],
        "target_client": target_fields["client"],
        "self_version": self_fields["version"],
        "target_version": target_fields["version"],
        "self_os": self_fields["os"],
        "target_os": target_fields["os"],
        "self_os_version": self_fields["os_version"],
        "target_os_version": target_fields["os_version"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/impersonate_target_contains_condition_snapshot/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/impersonate_target_contains_condition_snapshot/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_snapshot(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `test/qa/impersonate_target_contains_condition_snapshot_test.py`, class "
            "`TestImpersonateTargetContainsConditionSnapshotQA`, method "
            "`test_impersonate_target_contains_condition_snapshot_case`. "
            "The test does `result = OTHER_TARGET in SELF_TARGET`, which Python compiles "
            "into the call `SELF_TARGET.__contains__(OTHER_TARGET)`. "
            "`ImpersonateTarget.__contains__` is defined in "
            "`yt_dlp/networking/impersonate.py` at line 40. After the `isinstance` check "
            "at line 41 passes, control reaches the multi-conjunction return expression "
            "STARTING at line 43:\n"
            "```\n"
            "return (\n"
            "    (self.client is None or target.client is None or self.client == target.client)\n"
            "    and (self.version is None or target.version is None or self.version == target.version)\n"
            "    and (self.os is None or target.os is None or self.os == target.os)\n"
            "    and (self.os_version is None or target.os_version is None or self.os_version == target.os_version)\n"
            ")\n"
            "```\n"
            "At the line-43 trace event (the moment Python evaluates this return condition), "
            "report the EXACT values of every attribute referenced by the condition. "
            "`SELF_TARGET` and `OTHER_TARGET` are the two `ImpersonateTarget` dataclass "
            "instances built at the top of the test file with literal kwargs. Inside "
            "`__contains__`, `self` is the LEFT operand of `in` (i.e. `SELF_TARGET`, the "
            "container) and `target` is the RIGHT operand (i.e. `OTHER_TARGET`, the value "
            "being checked). "
            "Return a JSON object with exactly these eight keys (each value is either a "
            "string or null): `self_client`, `target_client`, `self_version`, "
            "`target_version`, `self_os`, `target_os`, `self_os_version`, "
            "`target_os_version`."
        ),
        "template_answer": {
            "self_client": "str_or_null",
            "target_client": "str_or_null",
            "self_version": "str_or_null",
            "target_version": "str_or_null",
            "self_os": "str_or_null",
            "target_os": "str_or_null",
            "self_os_version": "str_or_null",
            "target_os_version": "str_or_null",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
