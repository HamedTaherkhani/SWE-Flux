from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT_DIR = Path("/testbed")
TARGET_FILE_SUFFIX = "cfnlint/context/conditions/_utils.py"
TARGET_FUNC_QUAL = (
    "cfnlint.context.conditions._utils.build_instance_from_scenario"
)
INSTANCE_ID = "build_instance_from_scenario_is_root_invariant_suite"

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>\w+) ",
)

def _is_target_path(path: str) -> bool:
    return path.replace("\\", "/").endswith(TARGET_FILE_SUFFIX)

def _parse_changed_locals(raw_line: str) -> dict[str, object]:
    marker = " locals="
    idx = raw_line.find(marker)
    if idx < 0:
        return {}
    raw_locals = raw_line[idx + len(marker):].strip()
    try:
        parsed = ast.literal_eval(raw_locals)
    except (SyntaxError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    decoded: dict[str, object] = {}
    for k, v in parsed.items():
        if isinstance(v, str):
            try:
                decoded[k] = ast.literal_eval(v)
            except (SyntaxError, ValueError):
                decoded[k] = v
        else:
            decoded[k] = v
    return decoded

def extract_invariant(trace_text: str) -> dict[str, object]:
    observations: list[bool] = []
    relation_holds_for_all = True

    for raw_line in trace_text.splitlines():
        m = EVENT_RE.match(raw_line)
        if not m:
            continue
        if not _is_target_path(m.group("path")):
            continue
        if m.group("func") != TARGET_FUNC_QUAL:
            continue

        if m.group("event") != "call":
            continue

        changed = _parse_changed_locals(raw_line)
        is_root = changed.get("is_root")
        if not isinstance(is_root, bool):
            continue
        observations.append(is_root)
        if not is_root:
            relation_holds_for_all = False

    invariant_holds = bool(observations) and relation_holds_for_all
    return {
        "invariant_exists": invariant_holds,
        "observed_call_count": len(observations),
        "true_count": sum(1 for x in observations if x),
        "false_count": sum(1 for x in observations if not x),
        "first_samples": observations[:24],
    }

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
    extracted = extract_invariant(trace_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the full test suite in `tests/qa/testcase.py`, class "
            "`TestBuildInstanceFromScenarioIsRootInvariantSuiteQA` "
            "(21 tests). Each test calls "
            "`cfnlint.context.conditions._utils.build_instance_from_scenario("
            "instance, scenario, is_root=True, context=ctx)` (file "
            "`src/cfnlint/context/conditions/_utils.py`) on instances of "
            "varying shape -- scalars, empty / non-empty lists, "
            "single-Fn::If dicts at the root, multi-key dicts at the root, "
            "nested Fn::Ifs, lists of Fn::Ifs, ``Ref: AWS::NoValue`` "
            "short-circuits, deeply-nested mixed trees, and contexts that "
            "include / exclude `Fn::If` from `context.functions`. The "
            "function recurses along three distinct arms: an `Fn::If` arm "
            "that PROPAGATES `is_root` (passes the current frame's value, "
            "True or False), a list-iteration arm that passes "
            "`is_root=False`, and a dict-iteration arm (entered only when "
            "the current frame has `is_root == True`) that passes "
            "`is_root=False`. Across the entire test-suite execution, "
            "consider every Python `call` event of "
            "`build_instance_from_scenario`. At every such event, observe "
            "the parameter `is_root` and the parameter `instance`. Is the "
            "candidate variable invariant `is_root == True` always held? "
            "Return JSON as `{\\\"invariant_exists\\\": <bool>}` where "
            "`true` means the invariant holds for every observed call and "
            "`false` means it does not."
        ),
        "template_answer": {"invariant_exists": "bool"},
        "oracle_answer": {"invariant_exists": bool(extracted["invariant_exists"])},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_file": TARGET_FILE_SUFFIX,
            "trace_events": ["line", "call", "return", "exception"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::"
                "TestBuildInstanceFromScenarioIsRootInvariantSuiteQA"
            ),
            "observed_call_count": int(extracted["observed_call_count"]),
            "true_count": int(extracted["true_count"]),
            "false_count": int(extracted["false_count"]),
            "first_samples": list(extracted["first_samples"]),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
