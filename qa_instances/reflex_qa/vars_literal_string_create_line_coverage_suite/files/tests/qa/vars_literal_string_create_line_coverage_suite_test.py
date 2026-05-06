from __future__ import annotations

from reflex.vars.base import LiteralVar, Var
from reflex.vars.sequence import LiteralStringVar, StringVar


class TestVarsLiteralStringCreateLineCoverageOneQA:
    def test_single_state_var_between_literals(self):
        user = Var(_js_expr="state.user.name", _var_type=str)
        result = LiteralStringVar.create(f"hello {user}!")

        assert str(result) == '("hello "+state.user.name+"!")'


class TestVarsLiteralStringCreateLineCoverageTwoQA:
    def test_two_state_vars_with_literal_gap(self):
        first = Var(_js_expr="state.user.first", _var_type=str)
        last = Var(_js_expr="state.user.last", _var_type=str)
        result = LiteralStringVar.create(f"{first}::{last}")

        assert str(result) == '(state.user.first+"::"+state.user.last)'


class TestVarsLiteralStringCreateLineCoverageThreeQA:
    def test_adjacent_state_vars(self):
        left = Var(_js_expr="state.left", _var_type=str)
        right = Var(_js_expr="state.right", _var_type=str)
        result = LiteralStringVar.create(f"{left}{right}")

        assert str(result) == "(state.left+state.right)"


class TestVarsLiteralStringCreateLineCoverageFourQA:
    def test_integer_var_in_sentence(self):
        score = Var(_js_expr="state.metrics.score", _var_type=int)
        result = LiteralStringVar.create(f"score={score};")

        assert str(result) == '("score="+state.metrics.score+";")'


class TestVarsLiteralStringCreateLineCoverageFiveQA:
    def test_boolean_var_with_prefix_and_suffix(self):
        enabled = Var(_js_expr="state.flags.enabled", _var_type=bool)
        result = LiteralStringVar.create(f"enabled:{enabled}:done")

        assert str(result) == '("enabled:"+state.flags.enabled+":done")'


class TestVarsLiteralStringCreateLineCoverageSixQA:
    def test_literal_string_var_and_state_var(self):
        status = LiteralVar.create("ready").to(StringVar)
        user = Var(_js_expr="state.user.name", _var_type=str)
        result = LiteralStringVar.create(f"{status}-{user}")

        assert str(result) == '("ready"+"-"+state.user.name)'


class TestVarsLiteralStringCreateLineCoverageSevenQA:
    def test_repeated_state_var_tag(self):
        item = Var(_js_expr="state.item.label", _var_type=str)
        result = LiteralStringVar.create(f"[{item}]::{item}")

        assert str(result) == '("["+state.item.label+"]::"+state.item.label)'


class TestVarsLiteralStringCreateLineCoverageEightQA:
    def test_four_mixed_tags(self):
        alpha = Var(_js_expr="state.alpha", _var_type=str)
        beta = LiteralVar.create("B").to(StringVar)
        gamma = Var(_js_expr="state.gamma", _var_type=str)
        delta = LiteralVar.create("D").to(StringVar)
        result = LiteralStringVar.create(f"{alpha}|{beta}|{gamma}|{delta}")

        assert str(result) == '(state.alpha+"|"+"B"+"|"+state.gamma+"|"+"D")'


class TestVarsLiteralStringCreateLineCoverageNineQA:
    def test_requested_string_subclass_type(self):
        value = Var(_js_expr="state.path.slug", _var_type=str)
        result = LiteralStringVar.create(f"/page/{value}", _var_type=StringVar)

        assert str(result) == '("/page/"+state.path.slug)'
        assert isinstance(result, StringVar)


class TestVarsLiteralStringCreateLineCoverageTenQA:
    def test_long_literal_segments_around_three_vars(self):
        section = Var(_js_expr="router.page.params.section", _var_type=str)
        page = Var(_js_expr="router.page.params.page", _var_type=int)
        suffix = Var(_js_expr="state.route.suffix", _var_type=str)
        result = LiteralStringVar.create(
            f"/docs/archive/{section}/page/{page}/tail/{suffix}/index"
        )

        assert str(result) == (
            '("/docs/archive/"+router.page.params.section+"/page/"+'
            'router.page.params.page+"/tail/"+state.route.suffix+"/index")'
        )
