#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path


LINE_RE = re.compile(
    r"^(?P<path>[^:]+):(?P<lineno>\d+) (?P<func>\S+) event=line ",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Branch:
    label: str
    start: int
    end: int

    def contains(self, lineno: int) -> bool:
        return self.start <= lineno <= self.end


def _range_for_stmts(stmts: list[ast.stmt]) -> tuple[int, int]:
    if not stmts:
        raise ValueError("Empty branch body; expected at least one statement.")
    all_nodes = [n for s in stmts for n in ast.walk(s) if hasattr(n, "lineno")]
    start = min(getattr(n, "lineno") for n in all_nodes)  # type: ignore[arg-type]
    end = max(getattr(n, "end_lineno", getattr(n, "lineno")) for n in all_nodes)  # type: ignore[arg-type]
    return int(start), int(end)


def _find_target_if(source_text: str) -> tuple[ast.If, str]:
    tree = ast.parse(source_text)
    target_func = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_classify_token":
            target_func = node
            break
    if target_func is None:
        raise ValueError("Could not find function _classify_token.")

    wanted = '(mode in ("auto", "fast") and (a & 1)) or (mode == "strict" and a > pivot)'

    for stmt in target_func.body:
        if isinstance(stmt, ast.If):
            seg = ast.get_source_segment(source_text, stmt.test)
            if seg is not None and seg.strip() == wanted:
                return stmt, wanted
    raise ValueError("Could not locate the target if statement by condition text.")


def _collect_branches(target_if: ast.If) -> list[Branch]:
    branches: list[Branch] = []
    s, e = _range_for_stmts(target_if.body)
    branches.append(Branch("if", s, e))

    curr = target_if
    idx = 1
    while curr.orelse and len(curr.orelse) == 1 and isinstance(curr.orelse[0], ast.If):
        curr = curr.orelse[0]
        s, e = _range_for_stmts(curr.body)
        branches.append(Branch(f"elif_{idx}", s, e))
        idx += 1

    if curr.orelse:
        s, e = _range_for_stmts(curr.orelse)
        branches.append(Branch("else", s, e))
    else:
        raise ValueError("Expected a final else branch.")

    return branches


def _extract_executed_lines(trace_text: str, *, source_path_suffix: str) -> set[int]:
    executed: set[int] = set()
    for m in LINE_RE.finditer(trace_text):
        path = m.group("path").replace("\\", "/")
        if not path.endswith(source_path_suffix):
            continue
        executed.add(int(m.group("lineno")))
    if not executed:
        raise ValueError("No executed lines captured for target source file.")
    return executed


def extract_executed_branches(trace_text: str, *, source_text: str) -> dict[str, object]:
    target_if, wanted = _find_target_if(source_text)
    branches = _collect_branches(target_if)
    executed_lines = _extract_executed_lines(trace_text, source_path_suffix="yt_dlp/branch_suite.py")

    executed_labels: list[str] = []
    for br in branches:
        if any(br.contains(ln) for ln in executed_lines):
            executed_labels.append(br.label)

    if not executed_labels:
        raise ValueError("No branches detected as executed; trace/source mismatch?")

    return {
        "target_function": "_classify_token",
        "target_condition": wanted,
        "executed_branches": executed_labels,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/conditional_branches_suite/trace.log",
    )
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/branch_suite.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/conditional_branches_suite/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source).read_text(encoding="utf-8")
    oracle_answer = extract_executed_branches(trace_text, source_text=source_text)

    qa = {
        "question_kind": "conditional_statements",
        "question": (
            "Use `test/qa/conditional_branches_suite_test.py`, class "
            "`TestConditionalBranchesSuiteQA`, and execute the full test suite in that file "
            "(both test methods). Inside `yt_dlp/branch_suite.py`, function `_classify_token`, "
            "locate the single `if` statement whose condition text is exactly "
            "`(mode in (\"auto\", \"fast\") and (a & 1)) or (mode == \"strict\" and a > pivot)` "
            "(including parentheses and operators). Considering only the branches of that specific "
            "conditional chain (`if`, any `elif` blocks, and the final `else`), which branch blocks "
            "execute at least once across the entire test suite run? "
            "Return the answer as `executed_branches`, an ordered list of branch labels in source order "
            "using `if`, `elif_1`, `elif_2`, ..., `else`."
        ),
        "template_answer": {
            "executed_branches": ["str"],
        },
        "oracle_answer": {
            "executed_branches": oracle_answer["executed_branches"],
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
