from __future__ import annotations

from typing import TypedDict

from reflex.vars import Var
from reflex.vars.object import ObjectVar


class Profile(TypedDict):
    score: int
    tags: list[str]


class TestVarsObjectGetattrDefUsePairsQA:
    def test_vars_object_getattr_def_use_pairs_case(self):
        profile = Var(
            _js_expr="state.profile",
            _var_type=Profile,
        ).to(ObjectVar, Profile)

        score = profile.__getattr__("score")
        tags = profile.__getattr__("tags")

        assert str(score) == 'state.profile["score"]'
        assert score._var_type is int
        assert str(tags) == 'state.profile["tags"]'
        assert tags._var_type == list[str]
