"""Unit tests for the AST perturber (no Docker / no network)."""

from __future__ import annotations

import ast

from perturbation.config import PerturbationConfig
from perturbation.perturber import TestPerturber


def _perturb(src: str, strategy: str = "special_value", seed: int = 7, policy: str = "neutralize"):
    cfg = PerturbationConfig(repo="Keras", assertion_policy=policy)
    return TestPerturber(cfg).perturb(src, strategy_name=strategy, seed=seed)


def test_output_is_valid_python():
    src = "def f():\n    x = [1.0, 2.0]\n    assert len(x) == 2\n"
    res = _perturb(src)
    ast.parse(res.new_source)  # must parse


def test_structural_protection_and_value_change():
    src = (
        "import numpy as np\n"
        "def f():\n"
        "    x = np.array([-1.0, 0.5], dtype='float32')\n"
        "    y = g(x, value=0.2, axis=0, ndim=2)\n"
        "    self.assertEqual(x.shape, (2,))\n"
    )
    res = _perturb(src, strategy="special_value")
    tree = ast.parse(res.new_source)
    consts = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)]
    # dtype string preserved; structural kwargs axis/ndim preserved as 0 and 2.
    assert "float32" in consts
    assert 0 in consts and 2 in consts
    # the data kwarg `value` was changed away from its original
    assert res.n_changes > 0


def test_structural_kwargs_protected():
    src = "def f():\n    g(input_shape=(2, 3), units=4, value=0.7)\n"
    res = _perturb(src, strategy="special_value")
    tree = ast.parse(res.new_source)
    consts = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)]
    assert 2 in consts and 3 in consts and 4 in consts  # shape + units untouched


def test_assertions_neutralized():
    src = "def f():\n    x = 1.0\n    assert x == 1.0\n    self.assertEqual(x, 1.0)\n"
    res = _perturb(src, policy="neutralize")
    assert "assert " not in res.new_source
    assert "assertEqual" not in res.new_source


def test_pytest_raises_block_preserved():
    src = (
        "import pytest\n"
        "def f():\n"
        "    with pytest.raises(IndexError):\n"
        "        g(idx=5)\n"
    )
    res = _perturb(src)
    assert "pytest.raises(IndexError)" in res.new_source
    # the index inside the raises block must be untouched
    assert "idx=5" in res.new_source


def test_no_change_reports_zero():
    src = "def f():\n    return 'only strings here'\n"
    res = _perturb(src)
    assert res.n_changes == 0


def test_subscript_indices_protected():
    src = "def t():\n    mat[25, 6] = 0.5\n    y = arr[2] + 3.0\n"
    res = _perturb(src, strategy="special_value")
    # index literals untouched; data values may change
    assert "mat[25, 6]" in res.new_source
    assert "arr[2]" in res.new_source


def test_special_value_changes_values_and_preserves_types():
    src = "def f():\n    g(a=2.0, b=5)\n"
    res = _perturb(src, strategy="special_value")
    tree = ast.parse(res.new_source)
    # ast.unparse renders negatives as UnaryOp, so evaluate each kwarg node.
    by_kw = {
        kw.arg: ast.literal_eval(ast.unparse(kw.value))
        for c in ast.walk(tree) if isinstance(c, ast.Call)
        for kw in c.keywords
    }
    assert isinstance(by_kw["a"], float) and by_kw["a"] != 2.0
    assert isinstance(by_kw["b"], int) and by_kw["b"] != 5
