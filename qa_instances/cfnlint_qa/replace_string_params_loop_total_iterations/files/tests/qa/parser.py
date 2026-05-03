from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "replace_string_params_loop_total_iterations"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._language_extensions._Transform._replace_string_params"
)
TARGET_LINE = 211

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)
START_MARKER_RE = re.compile(r"\[TRACE\]\[START\]", re.MULTILINE)

def _split_segments(trace_text: str) -> list[str]:
    parts = START_MARKER_RE.split(trace_text)
    return [p for p in parts[1:] if p.strip()]

def _count_iterations(segment: str) -> int:
    count = 0
    for m in LINE_RE.finditer(segment):
        if m.group("func") != TARGET_FUNC_QUAL:
            continue
        if int(m.group("lineno")) != TARGET_LINE:
            continue
        count += 1
    return count

def extract_total_iterations(trace_text: str) -> int:
    segments = _split_segments(trace_text)
    if not segments:
        raise ValueError(
            "No [TRACE][START] markers found -- trace_plugin did not run."
        )
    per_test = [_count_iterations(seg) for seg in segments]
    if len(per_test) < 15:
        raise ValueError(
            f"Expected >= 15 test segments; found {len(per_test)}: {per_test}"
        )
    distinct = set(per_test)
    if len(distinct) != 1:
        raise ValueError(
            "Per-test iteration counts diverged across the suite: "
            f"{per_test}"
        )
    return per_test[0]

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log",
    )
    parser.add_argument(
        "--out",
        default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    total_iterations = extract_total_iterations(trace_text)

    qa = {
        "question_kind": "iterations",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestReplaceStringParamsLoopTotalIterationsQA`. The class "
            "contains 15 test methods "
            "(`test_replace_string_params_loop_total_iterations_case_01` "
            "through `..._case_15`). Each test method instantiates "
            "`cfnlint.template.transforms._language_extensions._Transform()` "
            "and performs a sequence of "
            "`t._replace_string_params(s, params)` invocations with "
            "varying `s` strings (some containing `${name}`/`&{name}` "
            "placeholders, some not) and varying `params` dicts (sizes "
            "0 to 12, sometimes with dict-valued entries). The 15 "
            "sequences differ in number of calls (1 to 12) and "
            "per-call shapes. "
            "QUESTION: how many times does the for-loop at line 210 "
            "of `src/cfnlint/template/transforms/_language_extensions.py` "
            "(`for k, v in params.items():` inside "
            "`_Transform._replace_string_params`) iterate its BODY "
            "during ONE such test method's execution? (The answer is "
            "invariant -- every one of the 15 test methods produces "
            "the same iteration count.) Return the answer under the "
            "field `total_iterations`. "
            "Reasoning rules to simulate (PER TEST): "
            "(a) Each call begins by evaluating "
            "`re.search(r\"(\\$|&){[a-zA-Z0-9\\.:]+}\", s)` at "
            "line 206. If `s` has NO `${name}` or `&{name}` "
            "substring, the function returns `(True, s)` at line 207 "
            "BEFORE entering the for-loop -- the call contributes 0 "
            "iterations regardless of `len(params)`. "
            "(b) Otherwise the for-loop at line 210 iterates "
            "EXACTLY `len(params)` times -- one body execution per "
            "key in `params.items()`. "
            "(c) Empty `params = {}` with a pattern-bearing `s` "
            "passes the regex guard but the loop has nothing to "
            "iterate -- the call contributes 0 iterations. "
            "(d) The intra-body `if isinstance(v, dict)` at line "
            "211 (which replaces dict values with an md5 hex "
            "prefix at lines 212-216) does NOT alter the iteration "
            "count. A param whose value is a dict still counts as "
            "exactly one iteration. "
            "(e) Whether a param's key actually appears in `s` is "
            "irrelevant to iter count -- the body's two `re.sub` "
            "calls at lines 217 and 218 just make zero substitutions "
            "for absent keys, but the iteration still counts. "
            "(f) The total per test is the SUM over all calls of "
            "`len(params)` for calls whose `s` contained a pattern, "
            "PLUS 0 for calls whose `s` did not."
        ),
        "template_answer": {
            "total_iterations": "int",
        },
        "oracle_answer": {"total_iterations": total_iterations},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["line"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestReplaceStringParamsLoopTotalIterationsQA"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
