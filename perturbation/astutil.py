"""Small shared AST helpers used by the perturber and the analyzers."""

from __future__ import annotations

import ast
from typing import Optional, Union

Number = Union[int, float]


def call_name(func: ast.AST) -> Optional[str]:
    """Best-effort dotted name for a call target (``np.zeros`` -> 'np.zeros')."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parent = call_name(func.value)
        return f"{parent}.{func.attr}" if parent else func.attr
    return None


def as_number(node: ast.AST) -> Optional[Number]:
    """Signed numeric value of a literal, handling ``-1.0`` (USub) etc.

    Returns the value (int/float) or ``None`` if the node is not a plain signed
    numeric literal. Booleans are excluded.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, (ast.USub, ast.UAdd))
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, (int, float))
        and not isinstance(node.operand.value, bool)
    ):
        value = node.operand.value
        return -value if isinstance(node.op, ast.USub) else value
    return None
