from __future__ import annotations

import argparse
import json
from pathlib import Path


QUESTION = (
    "Use `tests/qa/compiler_compile_unevaluated_page_direct_output_test.py`, "
    "class `TestCompilerCompileUnevaluatedPageDirectOutputQA`, method "
    "`test_compile_unevaluated_page_direct_output_case`. That test directly calls "
    "`reflex.compiler.compiler.compile_unevaluated_page` at "
    "`tests/qa/compiler_compile_unevaluated_page_direct_output_test.py:175`; "
    "the target function is defined at `reflex/compiler/compiler.py:739` and "
    "returns `(component, enable_state)` at `reflex/compiler/compiler.py:802`. "
    "Inside the target, local variable `component` is first assigned at "
    "`reflex/compiler/compiler.py:759`, styled at line 761, wrapped at line 781, "
    "and passed to `utils.add_meta` at lines 797-799. Local variable "
    "`enable_state` is initialized at `reflex/compiler/compiler.py:763` and may "
    "be set at lines 766-775. In the test, `CompileDirectState.flag`, "
    "`CompileDirectState.count`, and `CompileDirectState.labels` are declared at "
    "`tests/qa/compiler_compile_unevaluated_page_direct_output_test.py:24`, "
    ":25, and :26; they are used by `rx.cond` at line 41, `rx.text` at line 48, "
    "and `rx.foreach` at line 54. The foreach button event is created at line "
    "57, the increment button event chain at line 64, the page object at lines "
    "165-173, and the style argument at lines 179-183. The answer should be the "
    "summary produced from `component` and `enable_state` by `_summarize_return` "
    "at `tests/qa/compiler_compile_unevaluated_page_direct_output_test.py:145-160` "
    "after this direct call completes. What is the exact summarized return value "
    "of this direct function call? Return the object with exactly these keys: "
    "`returned_component_type`, `enable_state`, "
    "`top_level_child_types`, `main_child_types`, `main_style`, `imports`, "
    "`hook_count`, `refs`, `component_walk`, and `button_events`."
)


TEMPLATE_ANSWER = {
    "returned_component_type": "str",
    "enable_state": "bool",
    "top_level_child_types": ["str"],
    "main_child_types": ["str"],
    "main_style": {"str": "str"},
    "imports": ["str"],
    "hook_count": "int",
    "refs": ["str"],
    "component_walk": [
        {
            "depth": "int",
            "type": "str",
            "tag": "str | null",
            "id": "str | null",
            "children": "int",
            "events": ["str"],
        }
    ],
    "button_events": [
        {
            "path": "str",
            "text": ["str"],
            "custom_attrs": {"str": "str"},
            "events": [
                {
                    "handler": "str",
                    "client_handler": "str",
                    "args": [
                        {
                            "name": "str",
                            "expr": "str",
                            "literal": "int | str | null",
                        }
                    ],
                }
            ],
        }
    ],
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

    oracle_answer = extract_result(Path(args.pytest_log))
    oracle = {
        "question_kind": "C4_ProgramState",
        "question": QUESTION,
        "template_answer": TEMPLATE_ANSWER,
        "oracle_answer": oracle_answer,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(oracle, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps(oracle, indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
