from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT_DIR = Path("/testbed")
TARGET_FILE_SUFFIX = "cfnlint/jsonschema/_resolvers_cfn.py"
TARGET_FUNC_QUAL = (
    "cfnlint.jsonschema._resolvers_cfn._sub_parameter_expansion"
)
INSTANCE_ID = "sub_parameter_expansion_key_in_parameters_invariant_suite"

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=(?P<event>\w+) ",
)

def _is_target_path(path: str) -> bool:
    return path.replace("\\", "/").endswith(TARGET_FILE_SUFFIX)

def _parse_changed_locals(raw_line: str) -> dict[str, object]:
    marker = " locals="
    idx = raw_line.find(marker)
    if idx < 0:
        return {}
    raw_locals = raw_line[idx + len(marker):].strip()
    try:
        parsed = ast.literal_eval(raw_locals)
    except (SyntaxError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    decoded: dict[str, object] = {}
    for k, v in parsed.items():
        if isinstance(v, str):
            try:
                decoded[k] = ast.literal_eval(v)
            except (SyntaxError, ValueError):
                decoded[k] = v
        else:
            decoded[k] = v
    return decoded

_KEY_RE = re.compile(r"'([^']*)'\s*:")

def _key_in_dict_repr(key: str, value: object) -> bool | None:
    if isinstance(value, dict):
        return key in value
    if isinstance(value, str):
        s = value.strip()
        if not s.startswith("{") or not s.endswith("}"):
            return None
        inner = s[1:-1]
        depth = 0
        in_str: str | None = None
        out_keys: list[str] = []
        i = 0
        token_start: int | None = None
        while i < len(inner):
            ch = inner[i]
            if in_str is not None:
                if ch == "\\" and i + 1 < len(inner):
                    i += 2
                    continue
                if ch == in_str:
                    in_str = None
            else:
                if ch in ("'", '"'):
                    if depth == 0 and token_start is None:
                        token_start = i
                    in_str = ch
                elif ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    depth -= 1
                elif ch == ":" and depth == 0 and token_start is not None:
                    seg = inner[token_start:i].strip()
                    m = _KEY_RE.match(seg + ":")
                    if m:
                        out_keys.append(m.group(1))
                    token_start = None
            i += 1
        return key in out_keys
    return None

def extract_invariant(trace_text: str) -> dict[str, object]:
    frame_stack: list[dict[str, object]] = []
    observations: list[tuple[int, str, bool]] = []
    relation_holds_for_all = True

    for raw_line in trace_text.splitlines():
        m = EVENT_RE.match(raw_line)
        if not m:
            continue
        if not _is_target_path(m.group("path")):
            continue
        if m.group("func") != TARGET_FUNC_QUAL:
            continue

        event = m.group("event")
        lineno = int(m.group("lineno"))

        if event == "call":
            frame_stack.append({})
            changed = _parse_changed_locals(raw_line)
            if changed:
                frame_stack[-1].update(changed)
            continue
        if event in ("return", "exception"):
            if frame_stack:
                changed = _parse_changed_locals(raw_line)
                if changed:
                    frame_stack[-1].update(changed)
                frame_stack.pop()
            continue
        if event != "line" or not frame_stack:
            continue

        changed = _parse_changed_locals(raw_line)
        if changed:
            frame_stack[-1].update(changed)

        snap = frame_stack[-1]
        k = snap.get("key")
        p = snap.get("parameters")
        if not isinstance(k, str):
            continue
        in_p = _key_in_dict_repr(k, p)
        if in_p is None:
            continue
        observations.append((lineno, k, in_p))
        if not in_p:
            relation_holds_for_all = False

    invariant_holds = bool(observations) and relation_holds_for_all
    return {
        "invariant_exists": invariant_holds,
        "observed_event_count": len(observations),
        "violating_count": sum(1 for _, _, ok in observations if not ok),
        "violating_first": [(ln, k) for ln, k, ok in observations if not ok][:8],
        "sample": [(ln, k, ok) for ln, k, ok in observations[:14]],
    }

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
    extracted = extract_invariant(trace_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use the full test suite in `tests/qa/testcase.py`, class "
            "`TestSubParameterExpansionKeyInParametersInvariantSuiteQA` "
            "(21 tests). Each test invokes "
            "`cfnlint.jsonschema._resolvers_cfn.sub` (which delegates "
            "into the recursive helper `_sub_parameter_expansion`) on "
            "`Fn::Sub` instances of varying parameter count and shape -- "
            "bare-string and 2-element list forms; 0/1/2/3/4/6/7/8 "
            "parameters; pseudo Refs (`AWS::Region`, `AWS::Partition`); "
            "parameters that resolve via template `Default`, "
            "`AllowedValues[0]`, or remain unresolvable. Inside "
            "`_sub_parameter_expansion` (file "
            "`src/cfnlint/jsonschema/_resolvers_cfn.py`), the function "
            "first replaces its local `parameters` with `parameters.copy()` "
            "(line 395), then on the recursive arm pops the head key at "
            "line 407 (`value = parameters.pop(key)`). On the leaf arm "
            "(`len(parameters) == 1`), it iterates `for key, value in "
            "parameters.items():` at line 401 -- `key` is bound but not "
            "removed. Across the entire test-suite execution, sample two "
            "locals -- `key` and `parameters` -- at every Python `line` "
            "event of `_sub_parameter_expansion` where BOTH `key` is bound "
            "to a non-None string value AND `parameters` is bound to a "
            "dict. At every such event, is the candidate variable invariant "
            "`key in parameters` always held? Return JSON as "
            "`{\\\"invariant_exists\\\": <bool>}` where `true` means the "
            "invariant holds for every observed event and `false` means it "
            "does not."
        ),
        "template_answer": {"invariant_exists": "bool"},
        "oracle_answer": {"invariant_exists": bool(extracted["invariant_exists"])},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_file": TARGET_FILE_SUFFIX,
            "trace_events": ["line", "call", "return", "exception"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::"
                "TestSubParameterExpansionKeyInParametersInvariantSuiteQA"
            ),
            "observed_event_count": int(extracted["observed_event_count"]),
            "violating_count": int(extracted["violating_count"]),
            "violating_first": list(extracted["violating_first"]),
            "sample": list(extracted["sample"]),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
