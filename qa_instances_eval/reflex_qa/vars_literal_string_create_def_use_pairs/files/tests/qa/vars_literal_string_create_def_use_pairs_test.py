from __future__ import annotations

from reflex.vars.base import LiteralVar, Var
from reflex.vars.sequence import LiteralStringVar, StringVar


class TestVarsLiteralStringCreateDefUsePairsQA:
    def test_vars_literal_string_create_def_use_pairs_case(self):
        user_name = Var(_js_expr="state.user.name", _var_type=str)
        status = LiteralVar.create("done").to(StringVar)
        encoded_value = f"Hello {user_name}, status {status}!"

        result = LiteralStringVar.create(encoded_value)

        assert str(result) == '("Hello "+state.user.name+", status "+"done"+"!")'
        assert result._var_type is str

