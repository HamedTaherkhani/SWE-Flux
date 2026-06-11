#!/usr/bin/env python3
"""Oracle generator for the ``_parse_spec`` def-use intersection suite.

This computes def-use pairs from the *actual opcode execution* of the target
function rather than from a static AST map intersected with a line-level trace.
The static/line approach mis-attributes reads in two ways that matter here:

* boolean short-circuit -- on a single physical line such as
  ``check_sign(system_spec) and gain is not None`` the line fires whether or
  not the right operand is evaluated, so a co-located variable that was never
  read (``gain``) would be counted; and
* nested scopes -- a ``lambda``/comprehension body lives in its own code
  object, so names there (e.g. the lambda parameter ``spec`` on the
  ``check_sign = lambda spec: ...`` line) must not be attributed to this
  function.

Tracing ``LOAD_FAST``/``LOAD_DEREF`` and ``STORE_FAST``/``STORE_DEREF`` in the
target frame only makes both cases correct by construction.
"""
from __future__ import annotations

import argparse
import dis
import importlib
import importlib.util
import json
import sys
from pathlib import Path

INSTANCE_ID = "iosys_parse_spec_def_use_intersection_suite"
TARGET_FUNC_QUAL = "control.iosys._parse_spec"
TARGET_MODULE = "control.iosys"
TARGET_FUNC_NAME = "_parse_spec"
TEST_FILE = "tests/qa/iosys_parse_spec_def_use_intersection_suite_test.py"
TEST_CLASS = "TestParseSpecDefUseIntersectionQA"
NUM_TESTS = 10
TRACKED_VARS = {
    "dictname",
    "gain",
    "index",
    "nsignals",
    "signal_dict",
    "signal_indices",
    "signal_spec",
    "signame",
    "spec",
    "sys",
    "syslist",
    "syslist_index",
    "system_index",
    "system_spec",
}

LOAD_OPS = {"LOAD_FAST", "LOAD_DEREF"}
STORE_OPS = {"STORE_FAST", "STORE_DEREF"}


def _load_target():
    module = importlib.import_module(TARGET_MODULE)
    return getattr(module, TARGET_FUNC_NAME)


def _load_test_class(test_path: Path):
    spec = importlib.util.spec_from_file_location("qa_test_mod", str(test_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, TEST_CLASS)


def _resolve_test_path() -> Path:
    for candidate in (Path(TEST_FILE), Path("/testbed") / TEST_FILE):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"could not locate test file: {TEST_FILE}")


def extract_intersection():
    func = _load_target()
    code = func.__code__
    def_line = code.co_firstlineno
    param_names = code.co_varnames[: code.co_argcount + code.co_kwonlyargcount]
    param_init = {name: def_line for name in param_names if name in TRACKED_VARS}

    instr_by_offset = {ins.offset: ins for ins in dis.get_instructions(code)}
    cls = _load_test_class(_resolve_test_path())
    methods = [f"test_case_{i:02d}" for i in range(1, NUM_TESTS + 1)]

    per_test: list[set[tuple[str, int, int]]] = []
    for method in methods:
        pairs: set[tuple[str, int, int]] = set()
        last_def: dict[str, int] = {}

        def tracer(frame, event, arg):
            # Only follow the target function's own frame; nested code objects
            # (lambdas, comprehensions) are intentionally not traced so their
            # locals are never attributed to this function.
            if event == "call":
                if frame.f_code is code:
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
        per_test.append(pairs)

    intersection = set.intersection(*per_test) if per_test else set()
    return [
        {"variable": var, "def_line": def_line_, "use_line": use_line}
        for var, def_line_, use_line in sorted(intersection, key=lambda item: (item[0], item[1], item[2]))
    ]


def main():
    parser = argparse.ArgumentParser()
    # --trace-log is accepted for compatibility with the shared eval harness but
    # is unused: this oracle is computed by re-executing the tests under an
    # opcode tracer rather than by parsing a line-level trace.
    parser.add_argument("--trace-log", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log")
    parser.add_argument("--out", default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json")
    args = parser.parse_args()
    observed_pairs = extract_intersection()
    tracked_vars = ", ".join(f"`{name}`" for name in sorted(TRACKED_VARS))
    tests = ", ".join(f"`test_case_{i:02d}`" for i in range(1, 11))
    qa = {
        "question_kind": "M4_DataFlow",
        "question": (
            f"Run the full test suite in `{TEST_FILE}` (all 10 test methods in "
            f"`{TEST_CLASS}`, in file order: {tests}). The tests import the target "
            "directly with `from control.iosys import _parse_spec`. Focus only on "
            "function `control.iosys._parse_spec` in file `control/iosys.py`. Track "
            f"exactly these variable names: {tracked_vars}. For each of the 10 test "
            "methods, compute the unique def-use pairs observed during that method's "
            "execution of this function, then return only the pairs that are present "
            "in every one of the 10 per-test sets. A pair is present for a test method "
            "if, during that method's execution, the value assigned to `variable` at "
            "`def_line` is later read at `use_line` before that variable is redefined. "
            "Function parameters count as defined on the function definition line. "
            "Return the answer as `observed_def_use_pairs`, a list of objects with "
            "exactly these keys: `variable`, `def_line`, `use_line`. Sort the list by "
            "`variable` using Python's default case-sensitive string ordering, where "
            "uppercase letters sort before lowercase letters; then sort by `def_line`, "
            "then `use_line`, all ascending."
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
