from __future__ import annotations

import json

import reflex as rx
from reflex.components.base.bare import Bare
from reflex.utils.imports import ImportVar
from reflex.vars import Var, VarData


class ImportProbeState(rx.State):
    """State used only to add state-context imports to VarData."""

    label: str = "probe"


class TestBaseBareGetAllImportsDictKeysQA:
    def test_base_bare_get_all_imports_dict_keys_case(self):
        supporting_box = rx.box(
            rx.text(ImportProbeState.label),
            id="supporting-box",
        )
        supporting_script = rx.script(
            "window.__qa_probe = true;",
            id="supporting-script",
        )
        merged_var_data = VarData.merge(
            VarData.from_state(ImportProbeState, "label"),
            VarData(
                imports={
                    "custom-lib": [
                        ImportVar(tag="Alpha"),
                        ImportVar(tag="Beta", alias="BetaAlias"),
                    ],
                    "@scope/pkg": [ImportVar(tag=None, render=False)],
                    "react": [ImportVar(tag="useMemo")],
                },
                hooks={"const localProbe = 1": None},
                components=[supporting_box, supporting_script],
            ),
        )
        bare = Bare.create(
            Var(
                _js_expr="complexImportProbe",
                _var_type=str,
                _var_data=merged_var_data,
            )
        )

        imports = bare._get_all_imports(collapse=False)
        var_data = bare.contents._get_all_var_data()
        result = {
            "imports.keys()": sorted(imports.keys()),
            "imports.items()": {
                key: sorted(str(import_var) for import_var in value)
                for key, value in imports.items()
            },
            "var_data.imports": {
                key: sorted(str(import_var) for import_var in value)
                for key, value in var_data.imports
            },
            "var_data.components": [
                {"__class__": type(component).__name__}
                for component in var_data.components
            ],
        }
        print("QA_RESULT_JSON=" + json.dumps(result, sort_keys=True))

        assert "custom-lib" in result["imports.keys()"]
        assert "$/utils/context" in result["imports.keys()"]
