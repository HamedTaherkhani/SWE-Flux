#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

TARGET_FILE = Path("/testbed/yt_dlp/utils/_utils.py")
TARGET_FUNC_NAME = "decode"
TARGET_CLASS_NAME = "LenientJSONDecoder"
PARAM_DEF_LINE = 560  # `def decode(self, s):`
EXCLUDE_VARS = {"self"}

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

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:  # noqa: N802
        # `except X as name:` -- bind `name` at the handler's lineno.
        if node.name is not None:
            self.defs[node.lineno].add(node.name)
        self.generic_visit(node)


def get_target_function_node(module: ast.Module) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == TARGET_CLASS_NAME:
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == TARGET_FUNC_NAME:
                    return child
    raise ValueError(f"Could not find {TARGET_CLASS_NAME}.{TARGET_FUNC_NAME} in target file.")


def build_def_use_maps(file_text: str):
    module = ast.parse(file_text)
    func_node = get_target_function_node(module)

    visitor = DefUseVisitor()
    visitor.visit(func_node)

    param_names = {arg.arg for arg in func_node.args.args}

    all_local_defs: set[str] = set()
    for names in visitor.defs.values():
        all_local_defs.update(names)
    tracked_vars = (all_local_defs | param_names) - EXCLUDE_VARS

    filtered_defs: dict[int, set[str]] = {}
    filtered_uses: dict[int, set[str]] = {}
    for line, names in visitor.defs.items():
        keep = {n for n in names if n in tracked_vars and n not in EXCLUDE_VARS}
        if keep:
            filtered_defs[line] = keep
    for line, names in visitor.uses.items():
        keep = {n for n in names if n in tracked_vars and n not in EXCLUDE_VARS}
        if keep:
            filtered_uses[line] = keep
    return filtered_defs, filtered_uses, tracked_vars


def extract_observed_pairs(trace_text, defs_by_line, uses_by_line, tracked_vars):
    # Process events sequentially. `event=call` resets the per-frame `last_def`
    # snapshot to the param def-line. `event=return` and `event=exception` are
    # NOT used to gate frame liveness because `event=exception` also fires for
    # exceptions that propagate through but are caught higher up; we just skip
    # those event kinds for def-use bookkeeping.
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
            last_def = {"s": PARAM_DEF_LINE}
            continue

        if event in {"return", "exception"}:
            continue

        # event == "line"
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
        default="/testbed/logs/qa_instances/lenient_json_decoder_def_use_pairs/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/lenient_json_decoder_def_use_pairs/oracle.json",
    )
    args = parser.parse_args()

    source_text = TARGET_FILE.read_text(encoding="utf-8")
    defs_by_line, uses_by_line, tracked_vars = build_def_use_maps(source_text)

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    observed_pairs = extract_observed_pairs(
        trace_text, defs_by_line, uses_by_line, tracked_vars)

    qa = {
        "question_kind": "data_flow_prediction",
        "question": (
            "Use `test/qa/lenient_json_decoder_def_use_pairs_test.py`, class "
            "`TestLenientJsonDecoderDefUsePairsQA`, method "
            "`test_lenient_json_decoder_def_use_pairs_case`. "
            "Focus only on `LenientJSONDecoder.decode` (the method `decode` of class "
            "`LenientJSONDecoder` in `yt_dlp/utils/_utils.py`, with `def` at line 560 and "
            "body lines 561-576). The test creates a `LenientJSONDecoder(close_objects=2)` "
            "and then calls `decoder.decode(JSON_INPUT)` exactly once with the literal "
            "string `'{\"a\": 1, \"b\": [2, 3'` (a JSON snippet missing the closing `]` "
            "and `}`). "
            "Track only these local-scope variables for def-use pairing: "
            "`s` (the input parameter, considered DEFINED at the function's `def` line "
            "560 on each call entry, then redefined at lines 562 and 572 by the "
            "assignments `s = self.transform_source(s)` and `s = self._close_object(e)`); "
            "`attempt` (the for-loop variable bound at line 563); and `e` (the exception "
            "binding at line 568, `except json.JSONDecodeError as e:`). Do NOT track "
            "`self` or any attribute access via `self.X`. "
            "List ALL unique def-use pairs observed during this single test run for the "
            "tracked variables, where each pair `(variable, def_line, use_line)` means "
            "the value most recently assigned to `variable` at `def_line` is later read "
            "at `use_line` before any subsequent re-assignment of that variable. "
            "Return a JSON object with one key `observed_def_use_pairs`, a list of "
            "objects with exactly these keys: `variable`, `def_line`, `use_line`. Sort "
            "the list by `variable` then `def_line` then `use_line`, all ascending."
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
