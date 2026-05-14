#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

TARGET_FILE = Path("/testbed/reflex/vars/sequence.py")
TARGET_FUNC_QUAL = "reflex.vars.sequence.LiteralStringVar.create"
TARGET_LINE = 1206

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/reflex/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) (?P<rest>.*)$",
    re.MULTILINE,
)


def parse_locals(rest: str) -> dict[str, str]:
    marker = "locals="
    if marker not in rest:
        return {}
    locals_text = rest.split(marker, 1)[1]
    try:
        parsed = ast.literal_eval(locals_text)
    except (SyntaxError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def extract_offset_values(trace_text: str) -> list[int]:
    offset_values: list[int] = []
    frame_stack: list[dict[str, str]] = []

    for match in TRACE_RE.finditer(trace_text):
        path = match.group("path")
        func = match.group("func")
        event = match.group("event")
        lineno = int(match.group("lineno"))

        if path != str(TARGET_FILE) or func != TARGET_FUNC_QUAL:
            continue

        locals_delta = parse_locals(match.group("rest"))

        if event == "call":
            frame_stack.append(dict(locals_delta))
            continue

        if not frame_stack:
            continue

        if event in {"return", "exception"}:
            frame_stack.pop()
            continue

        frame_stack[-1].update(locals_delta)

        if lineno == TARGET_LINE:
            offset_repr = frame_stack[-1].get("offset")
            if offset_repr is None:
                raise ValueError("Target line was reached without local variable `offset`.")
            offset_values.append(int(ast.literal_eval(offset_repr)))

    if not offset_values:
        raise ValueError(f"No evaluations of line {TARGET_LINE} were observed.")

    return offset_values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/vars_literal_string_offset_invariant_suite/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/vars_literal_string_offset_invariant_suite/oracle.json",
    )
    args = parser.parse_args()

    offset_values = extract_offset_values(Path(args.trace_log).read_text(encoding="utf-8"))
    invariant_exists = all(offset == 0 for offset in offset_values)

    qa = {
        "question_kind": "M7_Invariants",
        "question": (
            "Use the full test suite in "
            "`tests/qa/vars_literal_string_offset_invariant_suite_test.py`: all tests in "
            "classes `TestVarsLiteralStringOffsetInvariantSingleEmbeddedQA`, "
            "`TestVarsLiteralStringOffsetInvariantMultipleEmbeddedQA`, and "
            "`TestVarsLiteralStringOffsetInvariantLiteralCollapseQA`, "
            "`TestVarsLiteralStringOffsetInvariantAdjacentVarsQA`, "
            "`TestVarsLiteralStringOffsetInvariantRepeatedVarQA`, "
            "`TestVarsLiteralStringOffsetInvariantLeadingLiteralQA`, "
            "`TestVarsLiteralStringOffsetInvariantTrailingLiteralQA`, "
            "`TestVarsLiteralStringOffsetInvariantNumberVarQA`, "
            "`TestVarsLiteralStringOffsetInvariantBooleanVarQA`, and "
            "`TestVarsLiteralStringOffsetInvariantFourTagsQA`. The direct calls to "
            "`LiteralStringVar.create(encoded_value)` are at test lines 12, 25, 39, 51, "
            "62, 73, 84, 95, 106, and 120. "
            "Focus on "
            "`reflex/vars/sequence.py`, class method "
            "`reflex.vars.sequence.LiteralStringVar.create`, lines 1167-1259. At line "
            "1206 (`offset += end - start`), consider local variable `offset` in the "
            "current invocation frame immediately before that line executes. Across all "
            "evaluations of this line over the full suite, is the property `offset == 0` "
            "an invariant property? Return JSON as `{\\\"invariant_exists\\\": <bool>}` "
            "where `true` means the property holds for every evaluation and `false` means "
            "it does not hold."
        ),
        "template_answer": {
            "invariant_exists": "bool",
        },
        "oracle_answer": {
            "invariant_exists": invariant_exists,
        },
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
