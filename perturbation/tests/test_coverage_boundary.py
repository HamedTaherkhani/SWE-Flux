"""Tests for coverage extraction and boundary strategies."""

from __future__ import annotations

import ast

from perturbation.analysis import TargetAnalyzer
from perturbation.config import PerturbationConfig
from perturbation.coverage import CoverageExtractor
from perturbation.perturber import TestPerturber

SAMPLE_TRACE = """\
[TRACE][START] pid=1 TRACE_OUT='x' TRACE_FILE='a.py'
2026-06-15 18:25:30.123 /testbed/keras/src/m.py:10 keras.src.m.relu event=call locals={}
2026-06-15 18:25:30.124 /testbed/keras/src/m.py:11 keras.src.m.relu event=line locals={}
2026-06-15 18:25:30.125 /testbed/keras/src/m.py:12 keras.src.m.relu event=line locals={}
2026-06-15 18:25:30.126 /testbed/keras/src/m.py:11 keras.src.m.relu event=return retval=1 locals={}
"""


def test_coverage_extracts_lines_and_edges():
    sig = CoverageExtractor().extract_text(SAMPLE_TRACE)
    assert ("keras/src/m.py", 10) in sig.lines
    assert ("keras/src/m.py", 12) in sig.lines
    # path prefix /testbed/ stripped
    assert all(not p.startswith("/testbed") for p, _ in sig.lines)
    # consecutive lines within the same function form edges
    assert ("keras.src.m.relu", 11, 12) in sig.edges
    # ordered events are retained for exact execution-path comparison
    assert sig.events[0] == ("keras/src/m.py", 10, "keras.src.m.relu", "call")
    assert sig.events[-1] == ("keras/src/m.py", 11, "keras.src.m.relu", "return")


def test_coverage_keeps_exact_event_sequence():
    loop_twice = """\
2026-06-15 18:25:30.123 /testbed/pkg/m.py:10 pkg.m.f event=call locals={}
2026-06-15 18:25:30.124 /testbed/pkg/m.py:11 pkg.m.f event=line locals={}
2026-06-15 18:25:30.125 /testbed/pkg/m.py:10 pkg.m.f event=line locals={}
2026-06-15 18:25:30.126 /testbed/pkg/m.py:11 pkg.m.f event=line locals={}
"""
    loop_thrice = """\
2026-06-15 18:25:30.123 /testbed/pkg/m.py:10 pkg.m.f event=call locals={}
2026-06-15 18:25:30.124 /testbed/pkg/m.py:11 pkg.m.f event=line locals={}
2026-06-15 18:25:30.125 /testbed/pkg/m.py:10 pkg.m.f event=line locals={}
2026-06-15 18:25:30.126 /testbed/pkg/m.py:11 pkg.m.f event=line locals={}
2026-06-15 18:25:30.127 /testbed/pkg/m.py:10 pkg.m.f event=line locals={}
2026-06-15 18:25:30.128 /testbed/pkg/m.py:11 pkg.m.f event=line locals={}
"""
    a = CoverageExtractor().extract_text(loop_twice)
    b = CoverageExtractor().extract_text(loop_thrice)
    assert a.lines == b.lines
    assert a.edges == b.edges
    assert a.events != b.events


def test_coverage_keeps_exception_events():
    trace = """\
2026-06-15 18:25:30.123 /testbed/pkg/m.py:10 pkg.m.f event=exception exc=ValueError locals={}
2026-06-15 18:25:30.124 /testbed/pkg/m.py:12 pkg.m.f event=exception exc=TypeError locals={}
"""
    sig = CoverageExtractor().extract_text(trace)
    assert sig.events == (
        ("pkg/m.py", 10, "pkg.m.f", "exception"),
        ("pkg/m.py", 12, "pkg.m.f", "exception"),
    )
    assert ("pkg/m.py", 10) in sig.lines
    assert ("pkg.m.f", 10, 12) in sig.edges


def test_coverage_new_lines_vs_baseline():
    full = CoverageExtractor().extract_text(SAMPLE_TRACE)
    smaller = CoverageExtractor().extract_text(
        "\n".join(SAMPLE_TRACE.splitlines()[:3])  # only up to line 11
    )
    assert ("keras/src/m.py", 12) in full.new_lines_vs(smaller)


def test_analyzer_collects_test_thresholds():
    tree = ast.parse("def t():\n    f(x, threshold=0.2, max_value=1.5)\n    g(-3)\n")
    analysis = TargetAnalyzer.from_test_tree(tree)
    assert 0.2 in analysis.thresholds and 1.5 in analysis.thresholds and -3.0 in analysis.thresholds


def test_analyzer_target_source_comparison_constants(tmp_path):
    src = tmp_path / "m.py"
    src.write_text("def relu(x):\n    if x > 0.7:\n        return x\n    return 0\n")
    analysis = TargetAnalyzer.from_target_source(src, ["keras.src.m.relu"])
    assert 0.7 in analysis.thresholds


def test_threshold_straddle_spreads_around_thresholds():
    cfg = PerturbationConfig(repo="Keras")
    src = (
        "import numpy as np\n"
        "def t():\n"
        "    x = np.array([0.0, 0.0, 0.0])\n"
        "    f(x, threshold=0.5)\n"
    )
    res = TestPerturber(cfg).perturb(src, strategy_name="threshold_straddle", seed=1)
    tree = ast.parse(res.new_source)
    arrays = [n for n in ast.walk(tree) if isinstance(n, ast.List)]
    assert arrays
    vals = []
    for elt in arrays[0].elts:
        try:
            vals.append(ast.literal_eval(ast.unparse(elt)))
        except Exception:
            pass
    # length is preserved (shape-safe) and at least one value straddles 0.5
    assert len(vals) == 3
    assert any(abs(v - 0.5) <= 0.1 for v in vals)


def test_preserve_length_keeps_vector_size():
    cfg = PerturbationConfig(repo="Keras", preserve_length=True)
    src = "import numpy as np\ndef t():\n    x = np.array([0.0, 0.0, 0.0, 0.0])\n    f(x, threshold=0.5)\n"
    res = TestPerturber(cfg).perturb(src, strategy_name="special_value", seed=1)
    tree = ast.parse(res.new_source)
    arr = [n for n in ast.walk(tree) if isinstance(n, ast.List)][0]
    assert len(arr.elts) == 4  # unchanged
