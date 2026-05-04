from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "language_extensions_replace_params_execution_path"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._language_extensions._Transform._replace_string_params"
)

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)

def extract_execution_path(trace_text: str) -> list[dict]:
    matches = [
        m for m in LINE_RE.finditer(trace_text)
        if m.group("func") == TARGET_FUNC_QUAL
    ]
    if not matches:
        raise ValueError(
            f"No event=line entries for {TARGET_FUNC_QUAL!r} found."
        )
    return [
        {
            "file": m.group("path").replace("/testbed/", ""),
            "func": m.group("func"),
            "line": int(m.group("lineno")),
        }
        for m in matches
    ]

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
    executed_path = extract_execution_path(trace_text)

    qa = {
        "question_kind": "control_flow_prediction",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestLanguageExtensionsReplaceParamsExecutionPathQA`, "
            "method `test_language_extensions_replace_params_execution_path_case`. "
            "The test instantiates "
            "`cfnlint.template.transforms._language_extensions._Transform` "
            "and calls "
            "`_Transform._replace_string_params(s, params)` (defined "
            "at lines 200-223 of "
            "`src/cfnlint/template/transforms/_language_extensions.py`) "
            "with: "
            "  s = \"stk-${Stage}-${Cfg}-${Env}-${Owner}-&{Stage}-tail\" "
            "  params = {"
            "\"Stage\":\"prod-1\","
            "\"Cfg\":{\"replicas\":3,\"name\":\"alpha\"},"
            "\"Env\":\"dev\","
            "\"Owner\":{\"team\":\"platform\",\"lead\":\"alice\"}"
            "}. "
            "Return the EXACT ordered execution path inside this "
            "function ONLY, as a list of objects with keys "
            "`file`, `func`, and `line`, INCLUDING repeated lines "
            "(every Python `line` event). Control-flow rules to "
            "simulate: "
            "(a) line 205 sets `pattern = r\"(\\$|&){[a-zA-Z0-9\\.:]+}\"`. "
            "(b) line 206 evaluates `re.search(pattern, s)`; the "
            "early-return at line 207 is taken iff that match is "
            "None. The crafted `s` DOES match, so 207 is NOT visited. "
            "(c) line 209 deepcopies `s` into `new_s`. "
            "(d) line 210 is the `for k, v in params.items()` head; "
            "it is RE-VISITED once per iteration (loop continuations "
            "land on this line again). "
            "(e) line 211 evaluates `isinstance(v, dict)`; when "
            "truthy, the multi-line statement at 212-216 computes the "
            "md5-digest hex fragment. CPython tracing typically emits "
            "ONE line event at line 212 for the start of that "
            "compound expression and may also emit events on the "
            "continuation lines (213-216). When `isinstance` is "
            "FALSE, lines 212-216 are SKIPPED entirely. "
            "(f) lines 217 and 218 (the two `re.sub` calls) ALWAYS "
            "execute on every iteration regardless of the dict "
            "branch. "
            "(g) after the for loop exits, line 220 evaluates "
            "`isinstance(s, str_node)`. The crafted input is a plain "
            "`str`, so line 221 is NOT visited. "
            "(h) line 223 is the final `return`. "
            "Note: `params` iterates in INSERTION order (Python 3.7+). "
            "Return the answer under the field `executed_path`."
        ),
        "template_answer": {
            "executed_path": [
                {"file": "str", "func": "str", "line": "int"}
            ],
        },
        "oracle_answer": {"executed_path": executed_path},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["line"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestLanguageExtensionsReplaceParamsExecutionPathQA::"
                "test_language_extensions_replace_params_execution_path_case"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
