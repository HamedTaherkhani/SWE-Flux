#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin records every line event for the test method (via TRACE_FILE
# matching the test file path). The test method body sequentially calls
# `SmoothValue.set` and `SmoothValue.reset` on a single object `sv`, then
# reads four attributes into local variables `final_value`, `final_smooth`,
# `final_initial`, `final_smoothing`. We snapshot these four locals at the
# RETURN event of the test method (FULL_LOCALS_ON_RETURN is enabled by the
# trace plugin's default settings, so the return event carries all locals).
EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/test/qa/smooth_value_post_set_reset_sequence_state_test\.py):"
    r"(?P<lineno>\d+) "
    r"(?P<func>\S+) "
    r"event=(?P<event>line|call|return|exception) ",
    re.MULTILINE,
)

RETURN_LOCALS_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/test/qa/smooth_value_post_set_reset_sequence_state_test\.py):"
    r"(?P<lineno>\d+) "
    r"(?P<func>\S+) "
    r"event=return retval=(?P<retval>.+?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

TARGET_METHOD_NAME_SUFFIX = ".test_smooth_value_post_set_reset_sequence_state_case"


def collect_final_state(trace_text: str) -> dict:
    target_locals: dict | None = None
    for m in RETURN_LOCALS_RE.finditer(trace_text):
        funcname = m.group("func")
        if funcname.endswith(TARGET_METHOD_NAME_SUFFIX):
            target_locals = ast.literal_eval(m.group("locals"))

    if target_locals is None:
        raise ValueError(
            f"No return event captured for test method ending in "
            f"{TARGET_METHOD_NAME_SUFFIX!r}.")

    required = ("final_value", "final_smooth", "final_initial", "final_smoothing")
    for name in required:
        if name not in target_locals:
            raise ValueError(
                f"Local {name!r} not in test-method return locals: {target_locals!r}")

    final_value = float(ast.literal_eval(target_locals["final_value"]))
    final_smooth = float(ast.literal_eval(target_locals["final_smooth"]))
    final_initial = float(ast.literal_eval(target_locals["final_initial"]))
    final_smoothing = float(ast.literal_eval(target_locals["final_smoothing"]))

    return {
        "final_value": round(final_value, 6),
        "final_smooth": round(final_smooth, 6),
        "final_initial": round(final_initial, 6),
        "final_smoothing": round(final_smoothing, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/smooth_value_post_set_reset_sequence_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/smooth_value_post_set_reset_sequence_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = collect_final_state(trace_text)

    qa = {
        "question_kind": "C4_ProgramState",
        "question": (
            "Use `test/qa/smooth_value_post_set_reset_sequence_state_test.py`, class "
            "`TestSmoothValuePostSetResetSequenceStateQA`, method "
            "`test_smooth_value_post_set_reset_sequence_state_case`. The test "
            "instantiates `yt_dlp.utils.progress.SmoothValue` (defined at line 96 in "
            "`yt_dlp/utils/progress.py`) and runs a sequence of `.set(...)` and "
            "`.reset()` method calls on a single object `sv`. The relevant `SmoothValue` "
            "definition is:\n"
            "```\n"
            " 96: class SmoothValue:\n"
            " 97:     def __init__(self, initial: float | None, smoothing: float):\n"
            " 98:         self.value = self.smooth = self._initial = initial\n"
            " 99:         self._smoothing = smoothing\n"
            "100:\n"
            "101:     def set(self, value: float):\n"
            "102:         self.value = value\n"
            "103:         if self.smooth is None:\n"
            "104:             self.smooth = self.value\n"
            "105:         else:\n"
            "106:             self.smooth = (1 - self._smoothing) * value + self._smoothing * self.smooth\n"
            "107:\n"
            "108:     def reset(self):\n"
            "109:         self.value = self.smooth = self._initial\n"
            "```\n\n"
            "The exact body of `test_smooth_value_post_set_reset_sequence_state_case` "
            "is:\n"
            "```\n"
            "sv = SmoothValue(2.0, 0.6)\n"
            "sv.set(10.0)\n"
            "sv.set(20.0)\n"
            "sv.set(5.0)\n"
            "sv.reset()\n"
            "sv.set(100.0)\n"
            "sv.set(50.0)\n"
            "sv.set(25.0)\n"
            "final_value = sv.value\n"
            "final_smooth = sv.smooth\n"
            "final_initial = sv._initial\n"
            "final_smoothing = sv._smoothing\n"
            "```\n\n"
            "Predict the FINAL VALUES of the four instance attributes of `sv` (i.e., "
            "`sv.value`, `sv.smooth`, `sv._initial`, `sv._smoothing`) at the moment the "
            "test method returns -- equivalently, the values of the four local "
            "variables `final_value`, `final_smooth`, `final_initial`, `final_smoothing` "
            "at the test method's return event. The arithmetic in `SmoothValue.set` "
            "uses Python floating-point: report each value computed exactly as Python "
            "would compute it, then ROUND to 6 decimal places using Python's "
            "`round(x, 6)` (banker's rounding) for the final answer.\n\n"
            "Return a JSON object with EXACTLY these four keys (each a float):\n"
            "- `final_value`: float -- `round(sv.value, 6)` at test-method return.\n"
            "- `final_smooth`: float -- `round(sv.smooth, 6)`.\n"
            "- `final_initial`: float -- `round(sv._initial, 6)`.\n"
            "- `final_smoothing`: float -- `round(sv._smoothing, 6)`."
        ),
        "template_answer": {
            "final_value": "float",
            "final_smooth": "float",
            "final_initial": "float",
            "final_smoothing": "float",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
