from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT_DIR = Path("/testbed")
TARGET_FILE_SUFFIX = "cfnlint/conditions/conditions.py"
TARGET_FUNC_QUAL = "cfnlint.conditions.conditions.Conditions.build_scenarios"
INSTANCE_ID = "conditions_build_scenarios_params_temporal_value_history"

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
    return parsed

def _decode_params_value(raw: object) -> dict[str, bool] | None:
    if not isinstance(raw, str):
        return None
    try:
        decoded = ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return None
    if not isinstance(decoded, dict):
        return None
    out: dict[str, bool] = {}
    for k, v in decoded.items():
        if not isinstance(k, str) or not isinstance(v, bool):
            return None
        out[k] = v
    return out

def extract_params_history(trace_text: str) -> list[dict[str, bool]]:
    frame_stack: list[dict[str, object]] = []
    history: list[dict[str, bool]] = []

    for raw_line in trace_text.splitlines():
        m = EVENT_RE.match(raw_line)
        if not m:
            continue
        if not _is_target_path(m.group("path")):
            continue
        if m.group("func") != TARGET_FUNC_QUAL:
            continue

        event = m.group("event")
        if event == "call":
            frame_stack.append({"params_repr": None})
            continue
        if event == "return":
            if frame_stack:
                frame_stack.pop()
            continue
        if event == "exception":
            continue
        if event != "line" or not frame_stack:
            continue

        changed = _parse_changed_locals(raw_line)
        if "params" not in changed:
            continue

        params_repr = changed["params"]
        if not isinstance(params_repr, str):
            continue
        if frame_stack[-1]["params_repr"] == params_repr:
            continue

        decoded = _decode_params_value(params_repr)
        if decoded is None:
            continue
        history.append(decoded)
        frame_stack[-1]["params_repr"] = params_repr
    return history

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
    history = extract_params_history(trace_text)

    qa = {
        "question_kind": "data_flow_prediction",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestConditionsBuildScenariosParamsTemporalHistoryQA`, method "
            "`test_conditions_build_scenarios_params_temporal_value_history_case`. "
            "Focus only on method "
            "`cfnlint.conditions.conditions.Conditions.build_scenarios` in file "
            "`src/cfnlint/conditions/conditions.py`. The method is a generator. "
            "After an early-return for empty `conditions` (line 209), it walks "
            "the input dict at lines 214-232 and PRE-FIXES every name whose "
            "value set is exactly `{True}` (line 216, appended to the hidden "
            "`conditions_set` dict) or exactly `{False}` (line 224, ditto); "
            "those names are dropped from `condition_names`. Every other name "
            "(including names absent from `self._conditions`, and names whose "
            "value set is `None` or `{True, False}`) is appended to "
            "`condition_names`. The function then iterates "
            "`for p in products:` over `itertools.product([True, False], "
            "repeat=len(condition_names))` and at line 248 rebinds "
            "`params = dict(zip(condition_names, p))`. This rebinding fires "
            "BEFORE any satisfiability check, so every product tuple yields a "
            "`params` binding regardless of whether the scenario is later "
            "yielded to the caller. (The empty-`condition_names` case still "
            "produces ONE binding because `itertools.product([True,False], "
            "repeat=0)` yields exactly one empty tuple, giving `params={}`.) "
            "If the inner loop at line 249 invokes "
            "`self._conditions[condition_name].build_true_cnf(...)` (line 252) "
            "or `.build_false_cnf(...)` (line 258) on a `condition_name` that "
            "isn't in `self._conditions`, the resulting `KeyError` is caught "
            "at line 272 and the generator returns -- so for unknown names, "
            "only the FIRST product tuple's `params` survives long enough to "
            "be observed. Across the entire test run, what is the ordered "
            "chronological sequence of all values bound to local `params` at "
            "line 248? Return the answer as `params_history`: a JSON array; "
            "each element is a JSON object whose keys are condition names "
            "(in `condition_names` insertion order) and whose values are "
            "booleans. Do not deduplicate -- if the tracer observes N "
            "rebindings, the array must have length N."
        ),
        "template_answer": {
            "params_history": [
                {"str": True},
                {},
            ]
        },
        "oracle_answer": {
            "params_history": history,
        },
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_file": TARGET_FILE_SUFFIX,
            "trace_events": ["line", "call", "return", "exception"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::"
                "TestConditionsBuildScenariosParamsTemporalHistoryQA::"
                "test_conditions_build_scenarios_params_temporal_value_history_case"
            ),
            "observed_binding_count": len(history),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
