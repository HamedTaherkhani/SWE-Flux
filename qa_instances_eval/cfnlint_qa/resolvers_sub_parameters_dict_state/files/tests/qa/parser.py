from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

INSTANCE_ID = "resolvers_sub_parameters_dict_state"
TARGET_FUNC_QUAL = (
    "cfnlint.jsonschema._resolvers_cfn._sub_parameter_expansion"
)

CALL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=call locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

def extract_parameters_state(trace_text: str) -> dict:
    matches = list(CALL_RE.finditer(trace_text))
    if not matches:
        raise ValueError(
            "No call events found in the trace log. Has the test driven "
            "cfnlint.jsonschema._resolvers_cfn.sub at all?"
        )

    target_locals_repr = None
    for m in matches:
        if m.group("func") != TARGET_FUNC_QUAL:
            continue
        target_locals_repr = m.group("locals")
        break

    if target_locals_repr is None:
        raise ValueError(
            "Could not find a call event for "
            f"{TARGET_FUNC_QUAL!r} in the trace log."
        )

    parsed_locals = ast.literal_eval(target_locals_repr)
    if "parameters" not in parsed_locals:
        raise ValueError(
            "Local variable `parameters` was not present in the call-event "
            f"locals: keys present = {sorted(parsed_locals.keys())!r}"
        )

    parameters_value = ast.literal_eval(parsed_locals["parameters"])
    if not isinstance(parameters_value, dict):
        raise ValueError(
            "Expected `parameters` to parse into a dict, got: "
            f"{type(parameters_value).__name__}"
        )

    return parameters_value

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
    parameters_value = extract_parameters_state(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestResolversSubParametersDictStateQA`, method "
            "`test_resolvers_sub_parameters_dict_state_case`. The test "
            "calls `cfnlint.jsonschema._resolvers_cfn.sub(validator, "
            "instance)` (defined at line 436 of "
            "`src/cfnlint/jsonschema/_resolvers_cfn.py`) with "
            "`instance = [\"${StackName}-${!literal}-${StackName}."
            "${Domain.Suffix}+${Env}_${Domain.Subdomain}@${Owner}\", "
            "{\"Env\": \"prod\", \"Domain.Suffix\": \"example.com\"}]`. "
            "Inside `sub`, the array branch executes: line 446 sets "
            "`string = instance[0]`; line 447 sets "
            "`parameters = deepcopy(instance[1])`; line 453 sets "
            "`sub_parameters = REGEX_SUB_PARAMETERS.findall(string)` "
            "(`REGEX_SUB_PARAMETERS = re.compile(r\"\\${\\s*([^!\\s]"
            ".*?)\\s*}\")` from `cfnlint.helpers`); the loop at lines "
            "454-460 iterates `sub_parameters` and -- for each name not "
            "already a key of `parameters` -- assigns "
            "`parameters[name] = {\"Fn::GetAtt\": name}` if `name` "
            "contains `.`, else `parameters[name] = {\"Ref\": name}`. "
            "Line 462 then iterates "
            "`for resolved_parameters in _sub_parameter_expansion("
            "validator, parameters)`. Capture the value of local "
            "variable `parameters` at the FIRST `call` event of "
            "`cfnlint.jsonschema._resolvers_cfn._sub_parameter_expansion` "
            "(i.e., the outermost invocation handed in by `sub`, BEFORE "
            "the helper performs its `parameters = parameters.copy()` "
            "rebind on line 395 and BEFORE any recursive `parameters."
            "pop(key)` on line 407). Return the answer as the field "
            "`parameters` whose value is a JSON object. Preserve the "
            "exact insertion-order of keys."
        ),
        "template_answer": {
            "parameters": {
                "<key>": "<str|object>",
            }
        },
        "oracle_answer": {
            "parameters": parameters_value,
        },
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["call"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestResolversSubParametersDictStateQA::"
                "test_resolvers_sub_parameters_dict_state_case"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
