from __future__ import annotations

from reflex.components.datadisplay.shiki_code_block import (
    ShikiBaseTransformers,
    ShikiCodeBlock,
    ShikiDecorations,
)
from reflex.components.radix.themes.layout.box import Box
from reflex.style import Style


class TestComponentsShikiCreateDefUsePairsQA:
    def test_components_shiki_create_def_use_pairs_case(self):
        transformers = [
            ShikiBaseTransformers(
                library="qa-transformers",
                fns=[],
                style=Style({"color": "tomato"}),
            ),
            {"name": "passthrough"},
        ]
        decorations = [
            {"start": 1, "end": 3, "tag_name": "mark"},
            ShikiDecorations(start=4, end=5),
        ]

        component = ShikiCodeBlock.create(
            "print('qa')",
            "caption",
            language="python",
            transformers=transformers,
            decorations=decorations,
            style={"background": "navy"},
            padding="2",
        )

        assert isinstance(component, Box)
        assert len(component.children) == 2
        assert component.children[0].code._var_value == "print('qa')"
        assert str(component.style["color"]) == '"tomato"'
        assert str(component.style["background"]) == '"navy"'
        assert str(component.style["padding"]) == '"2"'
