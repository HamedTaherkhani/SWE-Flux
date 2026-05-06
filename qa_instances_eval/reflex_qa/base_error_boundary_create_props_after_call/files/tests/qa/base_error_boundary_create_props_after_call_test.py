from __future__ import annotations

import json

import reflex as rx
from reflex.components.base.error_boundary import ErrorBoundary


class TestBaseErrorBoundaryCreatePropsAfterCallQA:
    def test_base_error_boundary_create_props_after_call_case(self):
        component = ErrorBoundary.create(
            rx.vstack(
                rx.text("alpha"),
                rx.button("beta", on_click=rx.console_log("beta")),
            )
        )

        fallback_render = component.fallback_render
        fallback_var_data = fallback_render._get_all_var_data()
        embedded_components = list(fallback_var_data.components)
        rendered_fallback = embedded_components[0].render()
        on_error_chain = component.event_triggers["on_error"]
        on_error_event = on_error_chain.events[0]

        result = {
            "props.keys()": sorted(component.get_props()),
            "props['on_error']": {
                "event_triggers.keys()": sorted(component.event_triggers),
                "events[0].handler": rx.utils.format.format_event_handler(
                    on_error_event.handler
                ),
                "events[0].args": [
                    {"arg._js_expr": arg._js_expr, "value.__str__()": str(value)}
                    for arg, value in on_error_event.args
                ],
            },
            "props['fallback_render']": {
                "__class__": type(fallback_render).__name__,
                "_var_type": fallback_render._var_type.__name__,
                "_get_all_var_data().components.__len__()": len(embedded_components),
                "_get_all_var_data().components[0].render()": rendered_fallback,
            },
            "component.children": [
                {"__class__": type(child).__name__} for child in component.children
            ],
        }
        print("QA_RESULT_JSON=" + json.dumps(result, sort_keys=True))

        assert result["props.keys()"] == [
            "fallback_render",
            "on_error",
        ]
        assert (
            result["props['fallback_render']"][
                "_get_all_var_data().components.__len__()"
            ]
            == 1
        )
