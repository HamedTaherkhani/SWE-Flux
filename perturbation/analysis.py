"""Static analysis to make perturbation code-aware.

Extracts candidate *branch thresholds* -- the numeric constants a test (and,
optionally, the target source file) compares against -- so boundary strategies
can deliberately straddle them instead of guessing.

Two sources:

* the **test module** itself: every numeric literal/kwarg it passes is a likely
  control parameter (e.g. ``threshold=0.2``, ``max_value=1.5``).
* the **target source** (optional): comparison constants in ``if``/``while``
  predicates of the function under test (``if x > 0`` -> ``0``). Requires the
  repo source to be available on the host; degrades gracefully when it is not.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from .astutil import as_number


@dataclass
class TargetAnalysis:
    thresholds: Tuple[float, ...] = ()
    source: str = ""  # "test", "target", or "test+target"

    def merged_with(self, other: "TargetAnalysis") -> "TargetAnalysis":
        vals = sorted(set(self.thresholds) | set(other.thresholds))
        tag = "+".join(t for t in (self.source, other.source) if t)
        return TargetAnalysis(tuple(vals), tag)


class TargetAnalyzer:
    """Collects numeric thresholds from test and (optionally) target source."""

    @staticmethod
    def _numeric_literals(tree: ast.AST) -> List[float]:
        vals: set[float] = set()
        for node in ast.walk(tree):
            v = as_number(node)
            if v is not None:
                vals.add(float(v))
        return sorted(vals)

    @classmethod
    def from_test_tree(cls, tree: ast.AST) -> TargetAnalysis:
        return TargetAnalysis(tuple(cls._numeric_literals(tree)), "test")

    @staticmethod
    def _comparison_constants(tree: ast.AST) -> List[float]:
        """Constants used in comparison predicates (richer branch boundaries)."""
        vals: set[float] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for operand in [node.left, *node.comparators]:
                    v = as_number(operand)
                    if v is not None:
                        vals.add(float(v))
        return sorted(vals)

    @classmethod
    def from_target_source(cls, source_path: Path, func_names: Optional[List[str]] = None) -> TargetAnalysis:
        """Parse a target source file for comparison constants.

        ``func_names`` (unqualified) narrows analysis to the functions of
        interest when given; otherwise the whole module is scanned.
        """
        try:
            text = Path(source_path).read_text(encoding="utf-8")
            tree = ast.parse(text)
        except (OSError, SyntaxError):
            return TargetAnalysis((), "")

        if func_names:
            wanted = {n.split(".")[-1] for n in func_names}
            consts: set[float] = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted:
                    consts.update(cls._comparison_constants(node))
            if consts:
                return TargetAnalysis(tuple(sorted(consts)), "target")

        return TargetAnalysis(tuple(cls._comparison_constants(tree)), "target")

    @classmethod
    def from_dotted_targets(cls, source_root: Path, dotted_names: List[str]) -> TargetAnalysis:
        """Resolve dotted ``TRACE_FUNC`` names to source files and pull thresholds.

        For a name like ``keras.src.backend.tensorflow.nn.relu`` we try the
        longest dotted prefix that maps to an existing ``.py`` file; the remaining
        tail is treated as the function to narrow on. Used when ``TRACE_FILE`` is
        empty and only dotted function names are given.
        """
        source_root = Path(source_root)
        vals: set[float] = set()
        for name in dotted_names:
            parts = [p for p in name.split(".") if p]
            for cut in range(len(parts), 0, -1):
                candidate = source_root.joinpath(*parts[:cut]).with_suffix(".py")
                if candidate.exists():
                    tail = parts[cut:]
                    func_names = [tail[-1]] if tail else None
                    vals |= set(cls.from_target_source(candidate, func_names).thresholds)
                    break
        return TargetAnalysis(tuple(sorted(vals)), "target")
