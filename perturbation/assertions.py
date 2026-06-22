"""Assertion-handling policies (Strategy pattern over AST).

The tests in this benchmark exist to *drive execution for tracing*; the ground
truth is re-derived by the per-instance ``parse_*_oracle.py`` from the trace, not
from the test's own assertions. Once we perturb inputs, the original assertions
(which hard-code the old expected values) may no longer hold and would abort the
harvest before the parser runs.

The default :class:`NeutralizeAssertions` policy therefore turns value
assertions into no-ops so the test still executes the target code and produces a
trace. ``with pytest.raises(...)`` blocks are deliberately left intact -- they
are part of the execution being measured, not a value check -- and inputs inside
them are not perturbed by the AST driver.
"""

from __future__ import annotations

import ast


def is_pytest_raises(node: ast.With) -> bool:
    """True if a ``with`` statement is a ``pytest.raises(...)`` context."""
    for item in node.items:
        call = item.context_expr
        if isinstance(call, ast.Call):
            func = call.func
            if isinstance(func, ast.Attribute) and func.attr == "raises":
                return True
            if isinstance(func, ast.Name) and func.id == "raises":
                return True
    return False


def _is_assert_call(node: ast.AST) -> bool:
    """Detect ``self.assertX(...)`` / ``np.testing.assert_*`` expression calls."""
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    func = node.value.func
    if isinstance(func, ast.Attribute):
        return func.attr.startswith("assert")
    if isinstance(func, ast.Name):
        return func.id.startswith("assert")
    return False


class AssertionPolicy(ast.NodeTransformer):
    """Base policy: identity transform (keep assertions as-is)."""

    name = "keep"

    def apply(self, tree: ast.AST) -> ast.AST:
        new = self.visit(tree)
        ast.fix_missing_locations(new)
        return new


class KeepAssertions(AssertionPolicy):
    name = "keep"


class NeutralizeAssertions(AssertionPolicy):
    """Replace value assertions with ``pass`` so harvesting cannot be blocked."""

    name = "neutralize"

    def visit_With(self, node: ast.With) -> ast.AST:
        # Leave pytest.raises bodies untouched (they are execution, not checks).
        if is_pytest_raises(node):
            return node
        return self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> ast.AST:
        return ast.copy_location(ast.Pass(), node)

    def visit_Expr(self, node: ast.Expr) -> ast.AST:
        if _is_assert_call(node):
            return ast.copy_location(ast.Pass(), node)
        return node


_POLICIES = {
    "keep": KeepAssertions,
    "neutralize": NeutralizeAssertions,
}


def get_policy(name: str) -> AssertionPolicy:
    if name not in _POLICIES:
        raise KeyError(f"Unknown assertion policy '{name}'. Available: {', '.join(_POLICIES)}")
    return _POLICIES[name]()
