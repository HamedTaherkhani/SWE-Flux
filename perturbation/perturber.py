"""AST-driven test perturber.

Drives a :class:`~perturbation.strategies.base.PerturbationStrategy` over a
test's source, protecting structural literals (shapes, dims, dtypes, indices)
and literals inside assertions / ``pytest.raises`` blocks, then re-emits source.

The strategy decides *how* to complicate a value; this driver decides *which*
literals are eligible. That separation keeps strategies tiny and the protection
rules in one place.
"""

from __future__ import annotations

import ast
import random
from typing import Optional, Tuple

from .assertions import get_policy, is_pytest_raises
from .astutil import as_number as _as_number, call_name as _call_name
from .config import PerturbationConfig
from .models import PerturbationResult
from .strategies import create as create_strategy
from .strategies.base import PerturbationContext, PerturbationStrategy


class _LiteralTransformer(ast.NodeTransformer):
    """Applies the strategy to eligible numeric literals only."""

    def __init__(
        self,
        strategy: PerturbationStrategy,
        rng: random.Random,
        config: PerturbationConfig,
        thresholds: Tuple[float, ...] = (),
    ) -> None:
        self.strategy = strategy
        self.rng = rng
        self.thresholds = thresholds
        self.config = config
        self.changes = 0
        self._kw_stack: list[Optional[str]] = []
        self._call_stack: list[Optional[str]] = []
        self._list_depth = 0

    # Never perturb inside assertions or pytest.raises blocks.
    def visit_Assert(self, node: ast.Assert) -> ast.AST:
        return node

    def visit_With(self, node: ast.With) -> ast.AST:
        if is_pytest_raises(node):
            return node
        return self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> ast.AST:
        func_name = _call_name(node.func)
        structural = self.config.is_structural_call(func_name)
        self._call_stack.append(func_name)

        node.func = self.visit(node.func)
        # Positional args of structural calls are shapes/ranges -> leave alone.
        if not structural:
            node.args = [self.visit(arg) for arg in node.args]

        new_keywords = []
        for kw in node.keywords:
            if self.config.is_structural_name(kw.arg):
                new_keywords.append(kw)  # protected structural kwarg
            else:
                self._kw_stack.append(kw.arg)
                kw.value = self.visit(kw.value)
                self._kw_stack.pop()
                new_keywords.append(kw)
        node.keywords = new_keywords

        self._call_stack.pop()
        return node

    def visit_Dict(self, node: ast.Dict) -> ast.AST:
        # Protect values of structurally-named string keys (e.g. {'units': 4}).
        new_values = []
        for key, value in zip(node.keys, node.values):
            key_name = key.value if isinstance(key, ast.Constant) and isinstance(key.value, str) else None
            if self.config.is_structural_name(key_name):
                new_values.append(value)
            else:
                self._kw_stack.append(key_name)
                new_values.append(self.visit(value))
                self._kw_stack.pop()
        node.values = new_values
        node.keys = [self.visit(k) if k is not None else None for k in node.keys]
        return node

    def _context(self) -> PerturbationContext:
        return PerturbationContext(
            rng=self.rng,
            keyword_name=self._kw_stack[-1] if self._kw_stack else None,
            enclosing_call=self._call_stack[-1] if self._call_stack else None,
            magnitude=self.config.magnitude,
            thresholds=self.thresholds,
            preserve_length=self.config.preserve_length,
        )

    @staticmethod
    def _flat_numeric_values(node: ast.List) -> Optional[list]:
        """Values of a flat numeric vector (signed literals ok), else None."""
        values = []
        for elt in node.elts:
            value = _as_number(elt)
            if value is None:
                return None
            values.append(value)
        return values or None

    def visit_List(self, node: ast.List) -> ast.AST:
        # Only grow top-level 1-D numeric vectors (never nested rows / shapes),
        # so multi-dimensional data stays rectangular.
        if self._list_depth == 0:
            values = self._flat_numeric_values(node)
            if values is not None:
                grown = self.strategy.perturb_sequence(values, self._context())
                if grown is not None and list(grown) != values:
                    node.elts = [ast.copy_location(ast.Constant(v), node) for v in grown]
                    self.changes += 1

        self._list_depth += 1
        node = self.generic_visit(node)  # then perturb individual elements
        self._list_depth -= 1
        return node

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        # Treat -1.0 / +3 as a single signed literal so the strategy sees the
        # real value (and we don't end up with "--1.0" from perturbing the
        # magnitude under a USub).
        value = _as_number(node)
        if value is None:
            return self.generic_visit(node)
        new_value = self.strategy.perturb_constant(value, self._context())
        if new_value is None or new_value == value:
            return node  # do not recurse into the operand
        self.changes += 1
        return ast.copy_location(ast.Constant(value=new_value), node)

    def visit_Subscript(self, node: ast.Subscript) -> ast.AST:
        # Indices/slices are positions, not data -- perturbing them causes
        # out-of-bounds errors (e.g. `mat[25, 6]`). Perturb the indexed object
        # expression but leave the index/slice untouched.
        node.value = self.visit(node.value)
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        value = node.value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return node
        new_value = self.strategy.perturb_constant(value, self._context())
        if new_value is None or new_value == value:
            return node
        self.changes += 1
        return ast.copy_location(ast.Constant(value=new_value), node)


class TestPerturber:
    """Perturb a single test module's source string."""

    __test__ = False  # not a pytest test class despite the "Test" prefix

    def __init__(self, config: PerturbationConfig, thresholds: Tuple[float, ...] = ()) -> None:
        self.config = config
        # Extra thresholds (e.g. from the target source) merged with the test's own.
        self._extra_thresholds = thresholds

    def perturb(self, source: str, *, strategy_name: str, seed: int) -> PerturbationResult:
        tree = ast.parse(source)

        # 0) candidate branch thresholds = the test's numeric literals plus any
        #    supplied from target-source analysis (used by boundary strategies).
        from .analysis import TargetAnalyzer  # local import to avoid cycle

        thresholds = tuple(
            sorted(set(TargetAnalyzer.from_test_tree(tree).thresholds) | set(self._extra_thresholds))
        )

        # 1) handle assertions first so protected literals inside them disappear
        #    (when neutralizing) or are skipped (when keeping).
        tree = get_policy(self.config.assertion_policy).apply(tree)

        # 2) perturb eligible input literals.
        strategy = create_strategy(strategy_name, self.config.magnitude)
        transformer = _LiteralTransformer(strategy, random.Random(seed), self.config, thresholds)
        tree = transformer.visit(tree)
        ast.fix_missing_locations(tree)

        new_source = ast.unparse(tree) + "\n"
        return PerturbationResult(
            new_source=new_source,
            n_changes=transformer.changes,
            strategy=strategy_name,
            seed=seed,
        )
