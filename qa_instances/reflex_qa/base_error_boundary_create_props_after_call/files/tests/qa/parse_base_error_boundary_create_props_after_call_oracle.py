from __future__ import annotations

import argparse
import json
from pathlib import Path


QUESTION = (
    "Use `tests/qa/base_error_boundary_create_props_after_call_test.py`, class "
    "`TestBaseErrorBoundaryCreatePropsAfterCallQA`, method "
    "`test_base_error_boundary_create_props_after_call_case`. The test directly "
    "calls `ErrorBoundary.create(...)` at "
    "`tests/qa/base_error_boundary_create_props_after_call_test.py:11-16` with one "
    "child component and assigns the returned `component` variable at line 11. The "
    "post-call variables `fallback_render`, `fallback_var_data`, "
    "`embedded_components`, `rendered_fallback`, `on_error_chain`, and "
    "`on_error_event` are assigned at "
    "`tests/qa/base_error_boundary_create_props_after_call_test.py:18-23`; the "
    "summarizing `result` dictionary is assigned at lines 25-46. The target method "
    "is `reflex.components.base.error_boundary.ErrorBoundary.create`; its function "
    "signature containing local dictionary variable `props` is at "
    "`reflex/components/base/error_boundary.py:46`. Inside the target, `props` is "
    "checked for `on_error` at lines 56-57, checked for `fallback_render` at line "
    "58, then `props['fallback_render']` is assigned from the nested "
    "`ArgsFunctionOperation.create(...)` call spanning lines 59-144. Immediately "
    "after that specific function call, execution reaches line 151 and passes "
    "`props` to `super().create`. What exact state does the `props`-derived "
    "component have after this call path, including the keys created in `props`, the "
    "default `on_error` event args, and the rendered default fallback component? "
    "Return exactly the code variable or attribute expressions shown as keys in the "
    "template."
)


TEMPLATE_ANSWER = {
    "props.keys()": ["str"],
    "props['on_error']": {
        "event_triggers.keys()": ["str"],
        "events[0].handler": "str",
        "events[0].args": [
            {"arg._js_expr": "str", "value.__str__()": "str"}
        ],
    },
    "props['fallback_render']": {
        "__class__": "str",
        "_var_type": "str",
        "_get_all_var_data().components.__len__()": "int",
        "_get_all_var_data().components[0].render()": {"str": "JSON value"},
    },
    "component.children": [{"__class__": "str"}],
}


def extract_result(pytest_log: Path) -> dict:
    for line in pytest_log.read_text(encoding="utf-8").splitlines():
        if "QA_RESULT_JSON=" in line:
            return json.loads(line.split("QA_RESULT_JSON=", 1)[1])
    raise RuntimeError(f"QA_RESULT_JSON marker not found in {pytest_log}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pytest-log", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    oracle = {
        "question_kind": "S4_ProgramState",
        "question": QUESTION,
        "template_answer": TEMPLATE_ANSWER,
        "oracle_answer": extract_result(Path(args.pytest_log)),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(oracle, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps(oracle, indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
