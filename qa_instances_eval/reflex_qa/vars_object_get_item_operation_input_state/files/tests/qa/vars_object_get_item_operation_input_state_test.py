from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

from reflex.vars import Var
from reflex.vars import object as object_mod
from reflex.vars.object import ObjectItemOperation, ObjectVar


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


class TestVarsObjectGetItemOperationInputStateQA:
    def test_vars_object_get_item_operation_input_state_case(self):
        captured = {}
        original_create = ObjectItemOperation.create
        profile = Var(
            _js_expr="state.profileById[selectedId]",
            _var_type=dict[str, int],
        ).to(ObjectVar, dict[str, int])

        def capture_create(cls, object, key, _var_type=None, _var_data=None):
            captured.update(
                {
                    "object": _value_summary(object),
                    "key": _value_summary(key),
                    "_var_type": _type_summary(_var_type),
                    "_var_data": None if _var_data is None else str(_var_data),
                }
            )
            return original_create.__func__(
                cls,
                object,
                key,
                _var_type=_var_type,
                _var_data=_var_data,
            )

        with patch.object(
            object_mod.ObjectItemOperation,
            "create",
            classmethod(capture_create),
        ):
            result = profile.get("score", -1)

        print("QA_RESULT_JSON=" + json.dumps(captured, sort_keys=True))

        assert str(result) == (
            '(isTrue(state.profileById[selectedId]["score"]) ? '
            'state.profileById[selectedId]["score"] : -1)'
        )
        assert captured["object"]["_js_expr"] == "state.profileById[selectedId]"
        assert captured["key"] == "score"
