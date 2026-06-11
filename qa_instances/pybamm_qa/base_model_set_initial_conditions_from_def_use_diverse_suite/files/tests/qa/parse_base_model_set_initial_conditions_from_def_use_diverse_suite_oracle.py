#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dis
import importlib
import importlib.util
import inspect
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("PYBAMM_DISABLE_TELEMETRY", "true")

INSTANCE_ID = "base_model_set_initial_conditions_from_def_use_diverse_suite"
TARGET_MODULE = "pybamm.models.base_model"
TARGET_CLASS_NAME = "BaseModel"
TARGET_FUNC_NAME = "set_initial_conditions_from"
TARGET_FUNC_QUAL = "pybamm.models.base_model.BaseModel.set_initial_conditions_from"
TARGET_FILE = "src/pybamm/models/base_model.py"
TEST_FILE = "tests/qa/base_model_set_initial_conditions_from_def_use_diverse_suite_test.py"
TEST_CLASS = "TestBaseModelSetInitialConditionsFromDefUseDiverseQA"
NUM_TESTS = 10
TRACKED_VARS = {
    "child",
    "children",
    "concatenated_initial_conditions",
    "equations",
    "final_state",
    "final_state_eval",
    "initial_conditions",
    "inplace",
    "model",
    "reference",
    "return_type",
    "scale",
    "slices",
    "solution",
    "sorted_equations",
    "symbol",
    "var",
    "y_slices",
}

LOAD_OPS = {"LOAD_FAST", "LOAD_DEREF"}
STORE_OPS = {"STORE_FAST", "STORE_DEREF"}


def _load_target():
    module = importlib.import_module(TARGET_MODULE)
    cls = getattr(module, TARGET_CLASS_NAME)
    return getattr(cls, TARGET_FUNC_NAME)


def _resolve_test_path() -> Path:
    parser_path = Path(__file__).resolve()
    instance_test_path = parser_path.with_name(
        "base_model_set_initial_conditions_from_def_use_diverse_suite_test.py"
    )
    for candidate in (Path(TEST_FILE), Path("/testbed") / TEST_FILE, instance_test_path):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"could not locate test file: {TEST_FILE}")


def _load_test_class(test_path: Path):
    spec = importlib.util.spec_from_file_location("qa_test_mod", str(test_path))
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"could not load test module from {test_path}")
    spec.loader.exec_module(module)
    return getattr(module, TEST_CLASS)


def _parameter_names(code) -> list[str]:
    names = list(code.co_varnames[: code.co_argcount + code.co_kwonlyargcount])
    next_index = code.co_argcount + code.co_kwonlyargcount
    if code.co_flags & inspect.CO_VARARGS:
        names.append(code.co_varnames[next_index])
        next_index += 1
    if code.co_flags & inspect.CO_VARKEYWORDS:
        names.append(code.co_varnames[next_index])
    return names


def _def_line(func) -> int:
    # ``co_firstlineno`` points at the first decorator for a decorated function;
    # the parameter "definition line" intended by the question is the line of the
    # ``def`` keyword itself, so skip any decorator lines.
    code = func.__code__
    try:
        lines, start = inspect.getsourcelines(func)
    except (OSError, TypeError):
        return code.co_firstlineno
    for offset, text in enumerate(lines):
        stripped = text.lstrip()
        if stripped.startswith(("def ", "async def ")):
            return start + offset
    return code.co_firstlineno


def extract_intersection():
    func = _load_target()
    code = func.__code__
    def_line = _def_line(func)
    param_init = {
        name: def_line for name in _parameter_names(code) if name in TRACKED_VARS
    }
    instr_by_offset = {ins.offset: ins for ins in dis.get_instructions(code)}
    cls = _load_test_class(_resolve_test_path())
    methods = [f"test_case_{i:02d}" for i in range(1, NUM_TESTS + 1)]
    per_test = []
    for method in methods:
        pairs = set()
        last_def = {}
        call_count = 0

        def tracer(frame, event, arg):
            nonlocal call_count
            if event == "call":
                if frame.f_code is code:
                    call_count += 1
                    frame.f_trace_opcodes = True
                    last_def.clear()
                    last_def.update(param_init)
                    return tracer
                return None
            if frame.f_code is not code:
                return tracer
            if event == "opcode":
                ins = instr_by_offset.get(frame.f_lasti)
                if ins is not None and ins.argval in TRACKED_VARS:
                    var = ins.argval
                    if ins.opname in LOAD_OPS and var in last_def:
                        pairs.add((var, last_def[var], frame.f_lineno))
                    elif ins.opname in STORE_OPS:
                        last_def[var] = frame.f_lineno
            return tracer

        sys.settrace(tracer)
        try:
            getattr(cls(), method)()
        finally:
            sys.settrace(None)
        if call_count != 1:
            raise RuntimeError(f"expected one target call in {method}, found {call_count}")
        per_test.append(pairs)

    unique_sets = {frozenset(pairs) for pairs in per_test}
    if len(unique_sets) < 2:
        raise RuntimeError("expected different per-test def-use sets, found only one")

    intersection = set.intersection(*per_test) if per_test else set()
    return [
        {"variable": var, "def_line": def_line_, "use_line": use_line}
        for var, def_line_, use_line in sorted(
            intersection, key=lambda item: (item[0], item[1], item[2])
        )
    ], len(unique_sets)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log")
    parser.add_argument("--out", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json")
    args = parser.parse_args()
    observed_pairs, unique_count = extract_intersection()
    tracked_vars = ", ".join(f"`{name}`" for name in sorted(TRACKED_VARS))
    tests = ", ".join(f"`test_case_{i:02d}`" for i in range(1, NUM_TESTS + 1))
    qa = {
        "question_kind": "M4_DataFlow",
        "question": (
            f"Run the full test suite in `{TEST_FILE}` (all 10 test methods in "
            f"`{TEST_CLASS}`, in file order: {tests}). The tests construct "
            "`pybamm.BaseModel` instances, then call the target method directly "
            "exactly once per test with dictionary-backed final-state data. Inputs "
            "cover single variables, concatenated domain variables, zero- through "
            "four-dimensional numpy arrays, discretised and non-discretised models, "
            "`return_type=\"model\"` versus `return_type=\"ics\"`, and both `inplace` "
            "settings. Focus only on method "
            f"`{TARGET_FUNC_QUAL}` in file `{TARGET_FILE}`. Track exactly these local "
            f"variable names: {tracked_vars}. A def-use pair is observed when a value "
            "assigned to a tracked variable at `def_line` is later read at `use_line` "
            "in the same call to this method before that variable is redefined. "
            "Function parameters count as definitions on the method definition line. "
            "Only count reads and writes in this method's own frame; do not count "
            "nested helper functions defined inside it or methods it calls. For each "
            "test method, compute the unique observed def-use pairs, then return only "
            "the pairs present in all 10 per-test sets. The per-test def-use sets are "
            "intentionally not all identical because the tests take different target "
            "branches. Return `observed_def_use_pairs` as a list of objects with "
            "exactly these keys: `variable`, `def_line`, `use_line`, sorted by "
            "`variable`, then `def_line`, then `use_line`, all ascending."
        ),
        "template_answer": {
            "observed_def_use_pairs": [
                {"variable": "str", "def_line": "int", "use_line": "int"}
            ]
        },
        "oracle_answer": {"observed_def_use_pairs": observed_pairs},
    }
    print(f"unique_per_test_def_use_set_count={unique_count}", file=sys.stderr)
    Path(args.out).write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
