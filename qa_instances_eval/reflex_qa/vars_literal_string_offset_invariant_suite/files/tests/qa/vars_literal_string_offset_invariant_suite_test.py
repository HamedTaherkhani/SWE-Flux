from __future__ import annotations

from reflex.vars.base import LiteralVar, Var
from reflex.vars.sequence import LiteralStringVar, StringVar


class TestVarsLiteralStringOffsetInvariantSingleEmbeddedQA:
    def test_single_state_var_tag(self):
        user_name = Var(_js_expr="state.user.name", _var_type=str)
        encoded_value = f"Hello {user_name}!"

        result = LiteralStringVar.create(encoded_value)

        assert str(result) == '("Hello "+state.user.name+"!")'
        assert result._var_type is str


class TestVarsLiteralStringOffsetInvariantMultipleEmbeddedQA:
    def test_three_mixed_var_tags(self):
        user_name = Var(_js_expr="state.user.name", _var_type=str)
        status = LiteralVar.create("ready").to(StringVar)
        count = Var(_js_expr="state.stats.count", _var_type=int)
        encoded_value = f"User {user_name} is {status} after {count} updates."

        result = LiteralStringVar.create(encoded_value)

        assert str(result) == (
            '("User "+state.user.name+" is "+"ready"+" after "+state.stats.count+" updates.")'
        )
        assert result._var_type is str


class TestVarsLiteralStringOffsetInvariantLiteralCollapseQA:
    def test_only_literal_string_var_tags(self):
        first = LiteralVar.create("north").to(StringVar)
        second = LiteralVar.create("south").to(StringVar)
        encoded_value = f"{first}-{second}"

        result = LiteralStringVar.create(encoded_value)

        assert str(result) == '("north"+"-"+"south")'
        assert result._var_type is str


class TestVarsLiteralStringOffsetInvariantAdjacentVarsQA:
    def test_adjacent_state_var_tags(self):
        first_name = Var(_js_expr="state.user.first", _var_type=str)
        last_name = Var(_js_expr="state.user.last", _var_type=str)
        encoded_value = f"{first_name}{last_name}"

        result = LiteralStringVar.create(encoded_value)

        assert str(result) == "(state.user.first+state.user.last)"
        assert result._var_type is str


class TestVarsLiteralStringOffsetInvariantRepeatedVarQA:
    def test_repeated_state_var_tag(self):
        item = Var(_js_expr="state.item.label", _var_type=str)
        encoded_value = f"[{item}]::{item}"

        result = LiteralStringVar.create(encoded_value)

        assert str(result) == '("["+state.item.label+"]::"+state.item.label)'
        assert result._var_type is str


class TestVarsLiteralStringOffsetInvariantLeadingLiteralQA:
    def test_long_leading_literal_before_var(self):
        page = Var(_js_expr="router.page.params.slug", _var_type=str)
        encoded_value = f"route-prefix-with-extra-text/{page}"

        result = LiteralStringVar.create(encoded_value)

        assert str(result) == '("route-prefix-with-extra-text/"+router.page.params.slug)'
        assert result._var_type is str


class TestVarsLiteralStringOffsetInvariantTrailingLiteralQA:
    def test_var_before_long_trailing_literal(self):
        title = Var(_js_expr="state.document.title", _var_type=str)
        encoded_value = f"{title}/archive/2026/final"

        result = LiteralStringVar.create(encoded_value)

        assert str(result) == '(state.document.title+"/archive/2026/final")'
        assert result._var_type is str


class TestVarsLiteralStringOffsetInvariantNumberVarQA:
    def test_number_var_inside_sentence(self):
        score = Var(_js_expr="state.metrics.score", _var_type=int)
        encoded_value = f"score={score};done"

        result = LiteralStringVar.create(encoded_value)

        assert str(result) == '("score="+state.metrics.score+";done")'
        assert result._var_type is str


class TestVarsLiteralStringOffsetInvariantBooleanVarQA:
    def test_boolean_var_between_literals(self):
        enabled = Var(_js_expr="state.flags.enabled", _var_type=bool)
        encoded_value = f"enabled:{enabled}:checked"

        result = LiteralStringVar.create(encoded_value)

        assert str(result) == '("enabled:"+state.flags.enabled+":checked")'
        assert result._var_type is str


class TestVarsLiteralStringOffsetInvariantFourTagsQA:
    def test_four_var_tags_with_literal_gaps(self):
        alpha = Var(_js_expr="state.alpha", _var_type=str)
        beta = LiteralVar.create("B").to(StringVar)
        gamma = Var(_js_expr="state.gamma", _var_type=str)
        delta = LiteralVar.create("D").to(StringVar)
        encoded_value = f"{alpha}|{beta}|{gamma}|{delta}"

        result = LiteralStringVar.create(encoded_value)

        assert str(result) == '(state.alpha+"|"+"B"+"|"+state.gamma+"|"+"D")'
        assert result._var_type is str
