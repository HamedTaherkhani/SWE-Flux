"""Pytest plugin that records per-test runtime metrics via sys.settrace.

For every collected test it traces *only* frames that belong to the target
repository (under METRICS_REPO_ROOT, excluding site-packages, the QA staging
dir, and test scaffolding) and accumulates dynamic characteristics:

  - function_calls       total in-repo function call events
  - total_lines_executed total in-repo line events (counts loop re-execution)
  - functions            distinct in-repo functions entered (file::name@firstline)
  - lines                distinct in-repo source lines executed (file:line)
  - files                distinct in-repo files touched
  - classes              distinct in-repo classes whose methods ran
  - max_stack_depth      deepest in-repo call stack reached

Why this naturally satisfies the requested exclusions:
  * sys.settrace only fires for *Python* frames, so C builtins such as
    len()/sum()/count()/print() never appear.
  * frames whose filename is not under the repo (i.e. other libraries in
    site-packages) are filtered out, so only the target repo is measured.

Class detection uses the runtime `self`/`cls` of each frame (works on every
Python version, including 3.10 which lacks co_qualname).

Configuration via env vars (set by incontainer_collect.py):
  METRICS_OUT                 path to append one JSON record per test
  METRICS_REPO_ROOT           repo checkout root (default /testbed)
  METRICS_FILE_INSTANCE_MAP   json: {abs_test_file: qa_instance_name}
"""

from __future__ import annotations

import json
import os
import sys

import pytest

REPO_ROOT = os.environ.get("METRICS_REPO_ROOT", "/testbed").rstrip("/")
OUT_PATH = os.environ["METRICS_OUT"]
# Set when an instance is run in isolation (its test file path collides with
# another instance's), so we can't rely on the file->instance map.
FORCE_INSTANCE = os.environ.get("METRICS_FORCE_INSTANCE") or None

try:
    with open(os.environ["METRICS_FILE_INSTANCE_MAP"], encoding="utf-8") as _fh:
        _FILE_INSTANCE_MAP = json.load(_fh)
except (KeyError, OSError, ValueError):
    _FILE_INSTANCE_MAP = {}

_SCAFFOLD_BASENAMES = {"conftest.py", "trace_plugin.py", "metrics_plugin.py"}


def _is_repo_file(fn: str) -> bool:
    fn = fn.replace("\\", "/")
    if not fn.startswith(REPO_ROOT + "/"):
        return False
    if "/site-packages/" in fn or "/dist-packages/" in fn:
        return False
    if "/qa_instances/" in fn or "/.venv/" in fn:
        return False
    # Exclude test scaffolding so we measure library behavior, not the driver.
    if fn.endswith("_test.py") or fn.endswith("_tests.py"):
        return False
    if "/test/" in fn or "/tests/" in fn or "/testing/" in fn:
        return False
    if fn.rsplit("/", 1)[-1] in _SCAFFOLD_BASENAMES:
        return False
    return True


def _relfn(fn: str) -> str:
    fn = fn.replace("\\", "/")
    prefix = REPO_ROOT + "/"
    return fn[len(prefix):] if fn.startswith(prefix) else fn


class _Collector:
    def __init__(self) -> None:
        self.function_calls = 0
        self.total_lines_executed = 0
        self.functions: set[str] = set()
        self.lines: set[str] = set()
        self.files: set[str] = set()
        self.classes: set[str] = set()
        self.depth = 0
        self.max_stack_depth = 0

    @staticmethod
    def _class_of(frame) -> str | None:
        loc = frame.f_locals
        obj = loc.get("self")
        cls = type(obj) if obj is not None else loc.get("cls")
        if not isinstance(cls, type):
            return None
        # Only count classes that are actually defined inside the target repo
        # (filters builtins, numpy/tf types, etc. that may sit in `self`).
        try:
            mod = sys.modules.get(cls.__module__)
            modfile = getattr(mod, "__file__", None)
        except Exception:
            modfile = None
        if not modfile or not _is_repo_file(modfile):
            return None
        return f"{cls.__module__}.{cls.__qualname__}"

    def global_trace(self, frame, event, arg):
        if event != "call":
            return None
        code = frame.f_code
        fn = code.co_filename
        if not _is_repo_file(fn):
            return None
        name = code.co_name
        if name == "<module>":
            return None  # module import execution, not a function call
        rel = _relfn(fn)
        self.files.add(rel)
        self.depth += 1
        if self.depth > self.max_stack_depth:
            self.max_stack_depth = self.depth
        # Comprehensions / generator exprs / lambdas (<listcomp> etc.) still
        # contribute covered lines, but are not counted as named functions.
        if not name.startswith("<"):
            self.function_calls += 1
            self.functions.add(f"{rel}::{name}@{code.co_firstlineno}")
            cls = self._class_of(frame)
            if cls is not None:
                self.classes.add(cls)
        return self.local_trace

    def local_trace(self, frame, event, arg):
        if event == "line":
            self.total_lines_executed += 1
            self.lines.add(f"{_relfn(frame.f_code.co_filename)}:{frame.f_lineno}")
        elif event == "return":
            if self.depth > 0:
                self.depth -= 1
        return self.local_trace

    def result(self) -> dict:
        return {
            "function_calls": self.function_calls,
            "total_lines_executed": self.total_lines_executed,
            "max_stack_depth": self.max_stack_depth,
            "functions": sorted(self.functions),
            "lines": sorted(self.lines),
            "files": sorted(self.files),
            "classes": sorted(self.classes),
        }


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    collector = _Collector()
    prev = sys.gettrace()
    sys.settrace(collector.global_trace)
    try:
        yield
    finally:
        sys.settrace(prev)

    inst = FORCE_INSTANCE or _FILE_INSTANCE_MAP.get(str(item.fspath))
    if inst is None:
        node_file = item.nodeid.split("::", 1)[0]
        for key, val in _FILE_INSTANCE_MAP.items():
            if key.endswith(node_file):
                inst = val
                break
    record = {
        "test_id": item.nodeid,
        "instance": inst or "",
        "metrics": collector.result(),
    }
    with open(OUT_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
