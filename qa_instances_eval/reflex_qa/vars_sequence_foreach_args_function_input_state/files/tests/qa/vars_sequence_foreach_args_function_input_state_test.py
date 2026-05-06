from __future__ import annotations

import json
from typing import Any, Callable
from unittest.mock import patch

from reflex.vars import Var
from reflex.vars import function as function_mod
from reflex.vars.function import ArgsFunctionOperation
from reflex.vars.sequence import ArrayVar


def _type_summary(value: Any) -> str | None:
    if value is None:
        return None
    return getattr(value, "__name__", str(value))


def _optional_attr(value: Any, name: str):
    try:
        return object.__getattribute__(value, name)
    except AttributeError:
        return None


def _value_summary(value: Any):
    if isinstance(value, tuple):
        return [_value_summary(item) for item in value]
    if isinstance(value, Var):
        summary = {
            "__class__": type(value).__name__,
            "_js_expr": value._js_expr,
            "_var_type": _type_summary(value._var_type),
            "_var_data": None if value._var_data is None else str(value._var_data),
        }
        var_value = _optional_attr(value, "_var_value")
        if var_value is not None:
            summary["_var_value"] = var_value
        original = _optional_attr(value, "_original")
        if original is not None:
            summary["_original._js_expr"] = original._js_expr
            summary["_original.__class__"] = type(original).__name__
        return summary
    return value


class TestVarsSequenceForeachArgsFunctionInputStateQA:
    def test_vars_sequence_foreach_args_function_input_state_case(self):
        captured = {}
        original_create = ArgsFunctionOperation.create
        rows = Var(
            _js_expr="state.rows.filter((row) => row.active)",
            _var_type=list[dict[str, int]],
        ).to(ArrayVar, list[dict[str, int]])

        def capture_create(
            cls,
            args_names,
            return_expr,
            rest=None,
            explicit_return=False,
            _var_type=Callable,
            _var_data=None,
        ):
            captured.update(
                {
                    "args_names": _value_summary(tuple(args_names)),
                    "return_expr": _value_summary(return_expr),
                    "rest": rest,
                    "explicit_return": explicit_return,
                    "_var_type": _type_summary(_var_type),
                    "_var_data": None if _var_data is None else str(_var_data),
                }
            )
            return original_create.__func__(
                cls,
                args_names,
                return_expr,
                rest=rest,
                explicit_return=explicit_return,
                _var_type=_var_type,
                _var_data=_var_data,
            )

        with (
            patch("reflex.vars.sequence.get_unique_variable_name", return_value="qa_row"),
            patch.object(
                function_mod.ArgsFunctionOperation,
                "create",
                classmethod(capture_create),
            ),
        ):
            result = rows.foreach(lambda item: item["score"] + item["bonus"] * 2)

        print("QA_RESULT_JSON=" + json.dumps(captured, sort_keys=True))

        assert str(result) == (
            'state.rows.filter((row) => row.active).map(((qa_row) => '
            '(qa_row["score"] + (qa_row["bonus"] * 2))))'
        )
        assert captured["args_names"] == ["qa_row"]
        assert captured["return_expr"]["_js_expr"] == '(qa_row["score"] + (qa_row["bonus"] * 2))'
