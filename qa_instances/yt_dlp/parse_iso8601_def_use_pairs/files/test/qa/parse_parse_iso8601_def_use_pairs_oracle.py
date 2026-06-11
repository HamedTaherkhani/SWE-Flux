#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

TARGET_FILE = Path("/testbed/yt_dlp/utils/_utils.py")
TARGET_FUNC_NAME = "parse_iso8601"
PARAM_DEF_LINE = 1214  # `def parse_iso8601(date_str, delimiter='T', timezone=None):`

TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/yt_dlp/utils/_utils\.py):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>call|line|return|exception) ",
    re.MULTILINE,
)


class DefUseVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.defs: dict[int, set[str]] = defaultdict(set)
        self.uses: dict[int, set[str]] = defaultdict(set)

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        if isinstance(node.ctx, ast.Store):
            self.defs[node.lineno].add(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.uses[node.lineno].add(node.id)
        elif isinstance(node.ctx, ast.Del):
            self.defs[node.lineno].add(node.id)
        self.generic_visit(node)


def get_target_function_node(module: ast.Module) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == TARGET_FUNC_NAME:
            return node
    raise ValueError(f"Could not find function {TARGET_FUNC_NAME} in target file.")


def build_def_use_maps(file_text: str):
    module = ast.parse(file_text)
    func_node = get_target_function_node(module)

    visitor = DefUseVisitor()
    visitor.visit(func_node)

    param_names = {arg.arg for arg in (
        func_node.args.args + func_node.args.kwonlyargs)}

    # Tracked = parameter names + names that are defined locally inside the
    # function. This automatically excludes module-level names like `re`,
    # `dt`, `calendar`, `extract_timezone`, `contextlib`, `ValueError`,
    # `TypeError`, `partial_application`.
    all_local_defs: set[str] = set()
    for names in visitor.defs.values():
        all_local_defs.update(names)
    tracked_vars = all_local_defs | param_names

    filtered_defs: dict[int, set[str]] = {}
    filtered_uses: dict[int, set[str]] = {}
    for line, names in visitor.defs.items():
        keep = {n for n in names if n in tracked_vars}
        if keep:
            filtered_defs[line] = keep
    for line, names in visitor.uses.items():
        keep = {n for n in names if n in tracked_vars}
        if keep:
            filtered_uses[line] = keep
    return filtered_defs, filtered_uses, tracked_vars, sorted(param_names)


def extract_observed_pairs(trace_text, defs_by_line, uses_by_line, tracked_vars,
                           param_names):
    pairs = set()
    last_def: dict[str, int] = {}

    for match in TRACE_RE.finditer(trace_text):
        path = match.group("path")
        func = match.group("func")
        event = match.group("event")
        lineno = int(match.group("lineno"))

        if path != str(TARGET_FILE) or not func.endswith(f".{TARGET_FUNC_NAME}"):
            continue

        if event == "call":
            last_def = {p: PARAM_DEF_LINE for p in param_names}
            continue

        if event in {"return", "exception"}:
            continue

        # event == "line"
        # Process USES first (use of the prior def), then DEFS (kill).
        for var in uses_by_line.get(lineno, set()):
            if var in last_def:
                pairs.add((var, last_def[var], lineno))

        for var in defs_by_line.get(lineno, set()):
            if var in tracked_vars:
                last_def[var] = lineno

    out = [
        {"variable": var, "def_line": d, "use_line": u}
        for (var, d, u) in sorted(pairs, key=lambda x: (x[0], x[1], x[2]))
    ]
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/parse_iso8601_def_use_pairs/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/parse_iso8601_def_use_pairs/oracle.json",
    )
    args = parser.parse_args()

    source_text = TARGET_FILE.read_text(encoding="utf-8")
    defs_by_line, uses_by_line, tracked_vars, param_names = build_def_use_maps(
        source_text)

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    observed_pairs = extract_observed_pairs(
        trace_text, defs_by_line, uses_by_line, tracked_vars, param_names)

    qa = {
        "question_kind": "S4_DataFlow",
        "question": (
            "Use `test/qa/parse_iso8601_def_use_pairs_test.py`, class "
            "`TestParseIso8601DefUsePairsQA`, method "
            "`test_parse_iso8601_def_use_pairs_case`. The test calls "
            "`yt_dlp.utils._utils.parse_iso8601(\"2024-03-15T10:30:00.123Z\")` -- the "
            "function `parse_iso8601` is defined at line 1214 in "
            "`yt_dlp/utils/_utils.py` (decorated with `@partial_application`, but with "
            "all required positional args supplied the wrapper delegates to the inner "
            "frame on every call). The function body is:\n"
            "```\n"
            "1214: def parse_iso8601(date_str, delimiter='T', timezone=None):\n"
            "1215:     \"\"\" Return a UNIX timestamp from the given date \"\"\"\n"
            "1216:\n"
            "1217:     if date_str is None:\n"
            "1218:         return None\n"
            "1219:\n"
            "1220:     date_str = re.sub(r'\\.[0-9]+', '', date_str)\n"
            "1221:\n"
            "1222:     timezone, date_str = extract_timezone(date_str, timezone)\n"
            "1223:\n"
            "1224:     with contextlib.suppress(ValueError, TypeError):\n"
            "1225:         date_format = f'%Y-%m-%d{delimiter}%H:%M:%S'\n"
            "1226:         dt_ = dt.datetime.strptime(date_str, date_format) - timezone\n"
            "1227:         return calendar.timegm(dt_.timetuple())\n"
            "```\n\n"
            "Track ONLY these local-scope variables for def-use pairing: parameters "
            "`date_str`, `delimiter`, `timezone` (each considered DEFINED at the "
            "function's `def` line 1214 on call entry), plus locals `date_format` "
            "(defined at line 1225 by `date_format = ...`) and `dt_` (defined at line "
            "1226 by `dt_ = ...`). Note that `date_str` is REDEFINED at line 1220 "
            "(`date_str = re.sub(...)`) and again at line 1222 (tuple-unpacked from "
            "`extract_timezone(...)`); `timezone` is REDEFINED at line 1222 "
            "(tuple-unpacked from the same call). DO NOT track module-level names "
            "(`re`, `dt`, `calendar`, `extract_timezone`, `contextlib`, "
            "`partial_application`) or builtins (`ValueError`, `TypeError`).\n\n"
            "List ALL UNIQUE def-use pairs OBSERVED during this single test run for "
            "the tracked variables, where each pair `(variable, def_line, use_line)` "
            "means: the value most recently assigned to `variable` at `def_line` is "
            "later READ at `use_line` BEFORE any subsequent re-assignment of that "
            "variable (within the same call frame). For lines where a variable is BOTH "
            "used and defined (e.g. line 1220 has `date_str` on the RHS and LHS), the "
            "USE is paired with the prior def, and then the DEF on that line replaces "
            "the active def for downstream uses.\n\n"
            "Return a JSON object with one key `observed_def_use_pairs`, a list of "
            "objects with exactly these keys: `variable`, `def_line`, `use_line`. Sort "
            "the list ascending by `variable`, then `def_line`, then `use_line`."
        ),
        "template_answer": {
            "observed_def_use_pairs": [
                {"variable": "str", "def_line": "int", "use_line": "int"},
            ],
        },
        "oracle_answer": {
            "observed_def_use_pairs": observed_pairs,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
