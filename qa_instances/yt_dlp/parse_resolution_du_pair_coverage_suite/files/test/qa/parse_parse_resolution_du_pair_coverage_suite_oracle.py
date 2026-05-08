#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


# The static DU-pair set for `parse_resolution(s, *, lenient=False)` is
# enumerated below by hand-applying reaching-definitions analysis to its CFG.
# Tracked variables: parameters `s`, `lenient`, and the local `mobj`. We
# exclude module/builtin globals (`re`, `int`).
#
# Source layout (lines 1856-1878):
#     1856: def parse_resolution(s, *, lenient=False):     # param defs of s, lenient
#     1857:     if s is None:                              # use s
#     1858:         return {}
#     1860:     if lenient:                                # use lenient
#     1861:         mobj = re.search(...lenient regex..., s)  # def mobj, use s
#     1862:     else:
#     1863:         mobj = re.search(...strict regex..., s)   # def mobj, use s
#     1864:     if mobj:                                   # use mobj
#     1865:         return {
#     1866:             'width': int(mobj.group('w')),     # use mobj
#     1867:             'height': int(mobj.group('h')),    # use mobj
#     1868:         }
#     1870:     mobj = re.search(...[pPiI] regex..., s)    # def mobj, use s
#     1871:     if mobj:                                   # use mobj
#     1872:         return {'height': int(mobj.group(1))}  # use mobj
#     1874:     mobj = re.search(...4k/8k regex..., s)     # def mobj, use s
#     1875:     if mobj:                                   # use mobj
#     1876:         return {'height': int(mobj.group(1)) * 540}  # use mobj
#     1878:     return {}
#
# Reaching defs:
#   - `s`: param def 1856 reaches every use of s (no redef).
#   - `lenient`: param def 1856 reaches its sole use at 1860.
#   - `mobj`: defs at 1861 (lenient=True path), 1863 (lenient=False path), 1870
#     (after 1864 falsy), 1874 (after 1871 falsy). 1861/1863 reach uses 1864,
#     1866, 1867. 1870 reaches uses 1871, 1872. 1874 reaches uses 1875, 1876.
#     1861/1863 do NOT reach 1871+ because 1870 redefines mobj. Etc.
STATIC_DU_PAIRS: set[tuple[str, int, int]] = {
    # s (5 pairs)
    ("s", 1856, 1857),
    ("s", 1856, 1861),
    ("s", 1856, 1863),
    ("s", 1856, 1870),
    ("s", 1856, 1874),
    # lenient (1 pair)
    ("lenient", 1856, 1860),
    # mobj (10 pairs)
    ("mobj", 1861, 1864), ("mobj", 1861, 1866), ("mobj", 1861, 1867),
    ("mobj", 1863, 1864), ("mobj", 1863, 1866), ("mobj", 1863, 1867),
    ("mobj", 1870, 1871), ("mobj", 1870, 1872),
    ("mobj", 1874, 1875), ("mobj", 1874, 1876),
}

PARAM_DEF_LINE = 1856

# Static def/use line tables (matching AST analysis, restricted to tracked vars).
DEFS_BY_LINE: dict[int, set[str]] = {
    1861: {"mobj"},
    1863: {"mobj"},
    1870: {"mobj"},
    1874: {"mobj"},
}
USES_BY_LINE: dict[int, set[str]] = {
    1857: {"s"},
    1860: {"lenient"},
    1861: {"s"},
    1863: {"s"},
    1864: {"mobj"},
    1866: {"mobj"},
    1867: {"mobj"},
    1870: {"s"},
    1871: {"mobj"},
    1872: {"mobj"},
    1874: {"s"},
    1875: {"mobj"},
    1876: {"mobj"},
}
TRACKED_VARS = {"s", "lenient", "mobj"}


EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.parse_resolution) "
    r"event=(?P<event>line|call|return|exception) ",
    re.MULTILINE,
)


def collect_observed_du_pairs(trace_text: str) -> set[tuple[str, int, int]]:
    observed: set[tuple[str, int, int]] = set()
    last_def: dict[str, int] = {}
    in_call = False

    for m in EVENT_RE.finditer(trace_text):
        ev = m.group("event")
        ln = int(m.group("lineno"))
        if ev == "call":
            last_def = {v: PARAM_DEF_LINE for v in ("s", "lenient")}
            in_call = True
            continue
        if ev == "return":
            in_call = False
            continue
        if ev == "exception":
            continue
        if ev == "line" and in_call:
            for v in USES_BY_LINE.get(ln, set()):
                if v in last_def:
                    observed.add((v, last_def[v], ln))
            for v in DEFS_BY_LINE.get(ln, set()):
                if v in TRACKED_VARS:
                    last_def[v] = ln

    return observed


def evaluate(observed: set[tuple[str, int, int]]) -> dict:
    covered = observed & STATIC_DU_PAIRS
    uncovered = STATIC_DU_PAIRS - observed
    spurious = observed - STATIC_DU_PAIRS  # should be empty if static set is correct

    def to_list(s):
        return [list(p) for p in sorted(s, key=lambda x: (x[0], x[1], x[2]))]

    return {
        "total_du_pairs_static": len(STATIC_DU_PAIRS),
        "covered_du_pairs_count": len(covered),
        "uncovered_du_pairs_count": len(uncovered),
        "is_all_du_pairs_covered": len(uncovered) == 0,
        "uncovered_du_pairs_list": to_list(uncovered),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/parse_resolution_du_pair_coverage_suite/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/parse_resolution_du_pair_coverage_suite/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    observed = collect_observed_du_pairs(trace_text)
    output = evaluate(observed)

    qa = {
        "question_kind": "coverage_prediction",
        "question": (
            "Use the FULL test suite in "
            "`test/qa/parse_resolution_du_pair_coverage_suite_test.py` (all 18 test "
            "methods in class `TestParseResolutionDuPairCoverageSuiteQA`). Each test "
            "method calls `yt_dlp.utils._utils.parse_resolution(<arg>)` (defined at line "
            "1856 in `yt_dlp/utils/_utils.py`, signature `parse_resolution(s, *, "
            "lenient=False)`). The function body is:\n"
            "```\n"
            "1856: def parse_resolution(s, *, lenient=False):\n"
            "1857:     if s is None:\n"
            "1858:         return {}\n"
            "1859: \n"
            "1860:     if lenient:\n"
            "1861:         mobj = re.search(r'(?P<w>\\d+)\\s*[xX×,]\\s*(?P<h>\\d+)', s)\n"
            "1862:     else:\n"
            "1863:         mobj = re.search(r'(?<![a-zA-Z0-9])(?P<w>\\d+)\\s*[xX×,]\\s*(?P<h>\\d+)(?![a-zA-Z0-9])', s)\n"
            "1864:     if mobj:\n"
            "1865:         return {\n"
            "1866:             'width': int(mobj.group('w')),\n"
            "1867:             'height': int(mobj.group('h')),\n"
            "1868:         }\n"
            "1869: \n"
            "1870:     mobj = re.search(r'(?<![a-zA-Z0-9])(\\d+)[pPiI](?![a-zA-Z0-9])', s)\n"
            "1871:     if mobj:\n"
            "1872:         return {'height': int(mobj.group(1))}\n"
            "1873: \n"
            "1874:     mobj = re.search(r'\\b([48])[kK]\\b', s)\n"
            "1875:     if mobj:\n"
            "1876:         return {'height': int(mobj.group(1)) * 540}\n"
            "1877: \n"
            "1878:     return {}\n"
            "```\n\n"
            "DEFINITIONS for this question:\n"
            "- TRACKED VARIABLES: `s` (positional parameter), `lenient` (keyword-only "
            "parameter), and `mobj` (a function-local variable). DO NOT track module-"
            "level names like `re` or builtins like `int`.\n"
            "- PARAM-DEF LINE: both `s` and `lenient` are considered DEFINED at the "
            "function's `def` line, 1856 (their initial binding on each call entry).\n"
            "- DEF lines for `mobj`: 1861, 1863, 1870, 1874 (each `mobj = re.search(...)` "
            "assignment).\n"
            "- USE lines for `s`: 1857, 1861, 1863, 1870, 1874.\n"
            "- USE lines for `lenient`: 1860.\n"
            "- USE lines for `mobj`: 1864, 1866, 1867, 1871, 1872, 1875, 1876.\n"
            "- A STATIC DU-PAIR is a triple `(variable, def_line, use_line)` such that "
            "there exists SOME execution path from `def_line` to `use_line` along which "
            "the variable is NOT redefined. Apply this to the function's control-flow "
            "graph: for example, both `(mobj, 1861, 1864)` and `(mobj, 1863, 1864)` are "
            "static DU-pairs because the lenient=True path defines `mobj` at 1861 and "
            "the lenient=False path defines `mobj` at 1863, with both paths flowing into "
            "the use at 1864 without redefinition. By contrast, `(mobj, 1861, 1871)` is "
            "NOT a static DU-pair, because every path from 1861 to 1871 must pass "
            "through the redefinition at 1870.\n"
            "- A static DU-pair `(v, d, u)` is COVERED by the test suite iff some test "
            "call's execution sees a line-event at `u` where the most recent def of `v` "
            "(at runtime) was at line `d`. Equivalently: at the line-`u` event, the last "
            "DEF of `v` to fire prior to `u` (within the same call frame) was at line "
            "`d`.\n\n"
            "Note: All 18 tests use the default `lenient=False` (the keyword-only "
            "argument is not overridden in any test).\n\n"
            "Return a JSON object with EXACTLY these five keys:\n"
            "- `total_du_pairs_static`: int -- the total number of static DU-pairs for "
            "the three tracked variables.\n"
            "- `covered_du_pairs_count`: int -- the number of static DU-pairs covered by "
            "at least one test call.\n"
            "- `uncovered_du_pairs_count`: int -- the number of static DU-pairs NOT "
            "covered by any test call.\n"
            "- `is_all_du_pairs_covered`: bool -- True iff `uncovered_du_pairs_count == "
            "0`.\n"
            "- `uncovered_du_pairs_list`: list of 3-element lists `[variable, def_line, "
            "use_line]`, sorted ascending by (variable, def_line, use_line). Each "
            "`variable` is one of the strings `\"s\"`, `\"lenient\"`, `\"mobj\"`. Empty "
            "list if all are covered."
        ),
        "template_answer": {
            "total_du_pairs_static": "int",
            "covered_du_pairs_count": "int",
            "uncovered_du_pairs_count": "int",
            "is_all_du_pairs_covered": "bool",
            "uncovered_du_pairs_list": [["str", "int", "int"]],
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
