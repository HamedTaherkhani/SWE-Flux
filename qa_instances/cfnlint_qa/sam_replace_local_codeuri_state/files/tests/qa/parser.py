from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

INSTANCE_ID = "sam_replace_local_codeuri_state"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._sam.Transform._replace_local_codeuri"
)

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=return retval=(?P<retval>.*?) "
    r"locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

def extract_resources_state(trace_text: str) -> dict:
    matches = [
        m for m in RETURN_RE.finditer(trace_text)
        if m.group("func") == TARGET_FUNC_QUAL
    ]
    if not matches:
        raise ValueError(
            f"No return events for {TARGET_FUNC_QUAL!r} found in the trace log."
        )

    last = matches[-1]
    parsed_locals = ast.literal_eval(last.group("locals"))

    if "all_resources" not in parsed_locals:
        raise ValueError(
            "Local variable `all_resources` was not present in the return-event "
            f"locals: keys present = {sorted(parsed_locals.keys())!r}"
        )

    resources = ast.literal_eval(parsed_locals["all_resources"])
    if not isinstance(resources, dict):
        raise ValueError(
            "Expected `all_resources` to parse into a dict, got: "
            f"{type(resources).__name__}"
        )
    return resources

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/trace.log",
    )
    parser.add_argument(
        "--out",
        default=f"/testbed/logs/qa_instances/{INSTANCE_ID}/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    resources = extract_resources_state(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestSamReplaceLocalCodeuriStateQA`, method "
            "`test_sam_replace_local_codeuri_state_case`. The test "
            "constructs a `cfnlint.template.transforms._sam.Transform` "
            "instance over `_TEMPLATE` and calls "
            "`Transform._replace_local_codeuri()` (defined at line 75 "
            "of `src/cfnlint/template/transforms/_sam.py`). That method "
            "binds `all_resources = self._template.get(\"Resources\", {})` "
            "(an alias by reference) and then walks every resource. It "
            "delegates the actual URI rewrite to the static helper "
            "`Transform._update_to_s3_uri(property_key, "
            "resource_property_dict, s3_uri_value=\"s3://bucket/value\")` "
            "(lines 257-285) whose contract is: read "
            "`resource_property_dict.get(property_key, \".\")`; if it "
            "is a dict AND `is_function(...)` returns a truthy key, "
            "OVERWRITE with `s3_uri_value`; if it is already an "
            "`\"s3://...\"` string, return without changing anything; "
            "otherwise OVERWRITE -- which means a *missing* key is ADDED "
            "with the s3 URI. Per-Type dispatch (skip resources whose "
            "`Properties` is missing or non-dict): "
            "(1) `AWS::Serverless::Function`: if "
            "`PackageType==\"Image\"` update `ImageUri` else update "
            "`CodeUri`; if `AutoPublishAlias` is a `{Ref: <name>}` and "
            "`<name>` is in the template's `Parameters` block, set "
            "`self._parameters[<name>] = \"Alias\"` (the alias dict "
            "itself is NOT modified); if `AutoPublishCodeSha256` is a "
            "dict, replace it with the literal string `\"fakesha\"`. "
            "(2) `AWS::Serverless::LayerVersion`: if `ContentUri` is "
            "truthy, update `ContentUri`. "
            "(3) `AWS::Serverless::Application`: if `Location` is "
            "truthy AND a dict, set `Location=\"\"` and then update "
            "`Location` (so it becomes `\"s3://bucket/value\"`); if "
            "`Location` is a non-empty STRING, NOTHING happens (the "
            "inner `isinstance(..., dict)` guard fails). "
            "(4) `AWS::Serverless::Api`: if NONE of "
            "`DefinitionBody`/`Auth`/`Cors`/`DisableExecuteApiEndpoint` "
            "is set, update `DefinitionUri` (adds the key if absent); "
            "otherwise OVERWRITE `DefinitionBody` with `\"\"` (adds it "
            "if absent). "
            "(5) `AWS::Serverless::StateMachine`: if `DefinitionUri` "
            "is truthy, update `DefinitionUri`. "
            "Capture the full state of local variable `all_resources` "
            "at the `return` event. Return the answer as the field "
            "`resources` whose value is a JSON object mirroring the "
            "post-method Resources dict. Preserve dict insertion order "
            "throughout (newly-added keys land at the END of the "
            "Properties dict)."
        ),
        "template_answer": {
            "resources": {"<resource_logical_id>": {"<key>": "<value>"}},
        },
        "oracle_answer": {"resources": resources},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["return"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestSamReplaceLocalCodeuriStateQA::"
                "test_sam_replace_local_codeuri_state_case"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
