from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

INSTANCE_ID = "template_search_deep_keys_outer_paths_state"
TARGET_FUNC_QUAL = (
    "cfnlint.template.template.Template._search_deep_keys"
)

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=return retval=(?P<retval>.*?) "
    r"locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

def extract_outer_keys(trace_text: str) -> list:
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

    if "keys" not in parsed_locals:
        raise ValueError(
            "Local variable `keys` was not present in the final return-event "
            f"locals: keys present = {sorted(parsed_locals.keys())!r}"
        )

    keys_value = ast.literal_eval(parsed_locals["keys"])
    if not isinstance(keys_value, list):
        raise ValueError(
            "Expected `keys` to parse into a list, got: "
            f"{type(keys_value).__name__}"
        )
    return keys_value

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
    keys_value = extract_outer_keys(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestTemplateSearchDeepKeysOuterPathsStateQA`, method "
            "`test_template_search_deep_keys_outer_paths_state_case`. "
            "The test constructs `cfn = Template(\"\", _TEMPLATE)` and "
            "then calls `cfn.search_deep_keys(re.compile(r\"^Fn::\"), "
            "includeGlobals=False)`. Internally that drives "
            "`cfnlint.template.template.Template._search_deep_keys` "
            "(defined at line 351 of "
            "`src/cfnlint/template/template.py`) recursively over the "
            "template. The recursion semantics: for each dict, iterate "
            "keys in insertion order; for each key K, form "
            "`pathprop = path[:] + [K]`; if `re.match(searchText, K)` "
            "matches (and K is a str) then append `cfndict[K]` to "
            "`pathprop`, append a reference to that list to the local "
            "`keys`, then `pathprop = pathprop[:-1]` to drop the value "
            "BEFORE recursing; finally, if `cfndict[K]` is itself a "
            "dict OR a list, recurse with that pathprop -- so a "
            "matching dict/list value produces BOTH a primary entry "
            "AND further entries from the recursion into the value. "
            "For list values, iterate `enumerate(...)` and recurse "
            "with `pathprop + [index]` for each item. The constructor "
            "of `Template` itself performs five separate scans for "
            "`\"Ref\"`, `\"Fn::Sub\"`, `\"Fn::If\"`, `\"Fn::FindInMap\"`, "
            "and the `Fn::ForEach` token, but those use STRING "
            "searchText and complete BEFORE the test's regex-pattern "
            "call. Capture the value of local variable `keys` at the "
            "outermost `return` event of `_search_deep_keys` for the "
            "test's explicit pattern call. Return the answer as the "
            "field `outer_keys` whose value is a JSON array of arrays "
            "(each inner array is one matched path, ending with the "
            "matching value as the LAST element). Order them as the "
            "function actually returns them (depth-first, "
            "left-to-right per dict-iteration / per list-enumerate)."
        ),
        "template_answer": {
            "outer_keys": [
                ["str", "...", "<matching value>"],
            ]
        },
        "oracle_answer": {
            "outer_keys": keys_value,
        },
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["return"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestTemplateSearchDeepKeysOuterPathsStateQA::"
                "test_template_search_deep_keys_outer_paths_state_case"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
