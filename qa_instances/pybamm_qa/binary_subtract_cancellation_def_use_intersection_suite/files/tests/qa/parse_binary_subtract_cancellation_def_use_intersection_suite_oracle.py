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

INSTANCE_ID = "binary_subtract_cancellation_def_use_intersection_suite"
TARGET_MODULE = "pybamm.expression_tree.binary_operators"
TARGET_FUNC_NAME = "subtract"
TARGET_FUNC_QUAL = "pybamm.expression_tree.binary_operators.subtract"
TARGET_FILE = "src/pybamm/expression_tree/binary_operators.py"
TEST_FILE = "tests/qa/binary_subtract_cancellation_def_use_intersection_suite_test.py"
TEST_CLASS = "TestBinarySubtractCancellationDefUseIntersectionQA"
NUM_TESTS = 10
TRACKED_VARS = {
    "left",
    "left_dim_size",
    "out",
    "r_left",
    "r_right",
    "right",
    "right_dim_size",
}

LOAD_OPS = {"LOAD_FAST", "LOAD_DEREF"}
STORE_OPS = {"STORE_FAST", "STORE_DEREF"}


def _load_target():
    module = importlib.import_module(TARGET_MODULE)
    return getattr(module, TARGET_FUNC_NAME)


def _resolve_test_path() -> Path:
    parser_path = Path(__file__).resolve()
    instance_test_path = parser_path.with_name(
        "binary_subtract_cancellation_def_use_intersection_suite_test.py"
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

    per_test: list[set[tuple[str, int, int]]] = []
    for method in methods:
        pairs: set[tuple[str, int, int]] = set()
        last_def: dict[str, int] = {}
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
                    if ins.opname in LOAD_OPS:
                        defined_at = last_def.get(var)
                        if defined_at is not None:
                            pairs.add((var, defined_at, frame.f_lineno))
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

    intersection = set.intersection(*per_test) if per_test else set()
    return [
        {"variable": var, "def_line": def_line_, "use_line": use_line}
        for var, def_line_, use_line in sorted(
            intersection, key=lambda item: (item[0], item[1], item[2])
        )
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log")
    parser.add_argument("--out", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json")
    args = parser.parse_args()

    observed_pairs = extract_intersection()
    tracked_vars = ", ".join(f"`{name}`" for name in sorted(TRACKED_VARS))
    tests = ", ".join(f"`test_case_{i:02d}`" for i in range(1, NUM_TESTS + 1))
    qa = {
        "question_kind": "M5_DataFlow",
        "question": (
            f"Run the full test suite in `{TEST_FILE}` (all 10 test methods in "
            f"`{TEST_CLASS}`, in file order: {tests}). Each test builds nested "
            "`pybamm.Addition` expression trees using constructors, then calls the "
            "target function directly once as `pybamm.subtract(left, right)` on a "
            "`(anchor + right) - right` cancellation shape. Focus only on function "
            f"`{TARGET_FUNC_QUAL}` in file `{TARGET_FILE}`. Track exactly these "
            f"local variable names: {tracked_vars}. A def-use pair is observed when "
            "a value assigned to a tracked variable at `def_line` is later read at "
            "`use_line` in the same call to this function before that variable is "
            "redefined. Function parameters count as definitions on the function "
            "definition line. Only count reads and writes in this function's own "
            "frame; do not count helper functions or methods it calls. For each "
            "test method, compute the unique observed def-use pairs, then return "
            "only the pairs present in all 10 per-test sets. Return "
            "`observed_def_use_pairs` as a list of objects with exactly these keys: "
            "`variable`, `def_line`, `use_line`, sorted by `variable`, then "
            "`def_line`, then `use_line`, all ascending."
        ),
        "template_answer": {
            "observed_def_use_pairs": [
                {"variable": "str", "def_line": "int", "use_line": "int"}
            ]
        },
        "oracle_answer": {"observed_def_use_pairs": observed_pairs},
    }
    Path(args.out).write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
