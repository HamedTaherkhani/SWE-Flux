from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

ROOT_DIR = Path("/testbed")
TARGET_FILE_SUFFIX = "cfnlint/template/transforms/_language_extensions.py"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._language_extensions._ForEachCollection.values"
)
INSTANCE_ID = "language_extensions_foreach_random_string_length_invariant_suite"
EXPECTED_LEN = 7

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
    for key, value in parsed.items():
        if isinstance(value, str):
            try:
                decoded[key] = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                decoded[key] = value
        else:
            decoded[key] = value
    return decoded

def extract_invariant(trace_text: str) -> dict[str, object]:

    binding_count = 0
    relation_holds_for_all = True
    observed_lengths: set[int] = set()

    for raw_line in trace_text.splitlines():
        m = EVENT_RE.match(raw_line)
        if not m:
            continue
        if m.group("event") != "line":
            continue
        if not _is_target_path(m.group("path")):
            continue
        if m.group("func") != TARGET_FUNC_QUAL:
            continue

        changed = _parse_changed_locals(raw_line)
        if "v" not in changed:
            continue
        v_value = changed["v"]
        if not isinstance(v_value, str):
            continue

        binding_count += 1
        observed_lengths.add(len(v_value))
        if len(v_value) != EXPECTED_LEN:
            relation_holds_for_all = False

    invariant_holds = bool(binding_count) and relation_holds_for_all
    return {
        "invariant_exists": invariant_holds,
        "observed_binding_count": binding_count,
        "observed_lengths": sorted(observed_lengths),
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
        "question_kind": "M7_Invariants",
        "question": (
            "Use the full test suite in `tests/qa/testcase.py`, class "
            "`TestLanguageExtensionsForEachRandomStringLengthInvariantSuiteQA` "
            "(21 tests). Each test exercises "
            "`cfnlint.template.transforms._language_extensions._ForEachCollection.values` "
            "in `src/cfnlint/template/transforms/_language_extensions.py` along "
            "different control-flow paths: literal-list collections where every "
            "item is an unresolvable `Ref` and where every item is a resolvable "
            "scalar; mixed lists that interleave resolvable scalars, parameter "
            "Refs (resolved via `Default` and via `AllowedValues[0]`), pseudo "
            "Refs (`AWS::Region`, `AWS::Partition`, `AWS::URLSuffix`, "
            "`AWS::AccountId` -- the last unresolvable when the module-global "
            "`_ACCOUNT_ID` is None), and `Fn::FindInMap` items both with and "
            "without a 4th-element `DefaultValue`; `_fn` invocations whose "
            "single dict is an unresolvable Ref (random-fallback into the "
            "`for _ in range(0, 2)` loop), an unresolvable Ref replayed from a "
            "shared cache via `yield from iter(...)`, a resolvable "
            "`CommaDelimitedList` (yields `Fn::Select` dicts), an "
            "`Fn::FindInMap` whose 4th-element `DefaultValue` is itself a list, "
            "a Ref to a `List<...>` parameter with a comma-delimited `Default`, "
            "and chained-share-cache flows across multiple distinct Refs. "
            "Focus exclusively on the per-frame `line` events of "
            "`cfnlint.template.transforms._language_extensions._ForEachCollection.values` "
            "in which the local variable `v` is (re)bound to a string value "
            "(i.e. the two `v = \"\".join(random.choices(string.ascii_letters, k=_N))` "
            "assignments at the two `except _ResolveError` arms). Across every "
            "such binding event over the whole test suite, is the relationship "
            "`len(v) == 7` an invariant property? Return JSON as "
            "`{\\\"invariant_exists\\\": <bool>}` where `true` means the relationship "
            "holds for every observed binding and `false` means it does not."
        ),
        "template_answer": {
            "invariant_exists": "bool"
        },
        "oracle_answer": {
            "invariant_exists": bool(extracted["invariant_exists"]),
        },
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_file": TARGET_FILE_SUFFIX,
            "trace_events": ["line", "call", "return", "exception"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::"
                "TestLanguageExtensionsForEachRandomStringLengthInvariantSuiteQA"
            ),
            "observed_binding_count": int(extracted["observed_binding_count"]),
            "observed_lengths": list(extracted["observed_lengths"]),
            "expected_length": EXPECTED_LEN,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
