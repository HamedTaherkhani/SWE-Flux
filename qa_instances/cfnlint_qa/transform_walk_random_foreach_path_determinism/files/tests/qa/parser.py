from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "transform_walk_random_foreach_path_determinism"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._language_extensions._Transform._walk"
)

START_MARKER_RE = re.compile(r"\[TRACE\]\[START\]", re.MULTILINE)
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line ",
    re.MULTILINE,
)

def _split_segments(trace_text: str) -> list[str]:
    parts = START_MARKER_RE.split(trace_text)
    return [p for p in parts[1:] if p.strip()]

def _extract_sequence(segment: str) -> tuple[int, ...]:
    seq: list[int] = []
    for m in LINE_RE.finditer(segment):
        if m.group("func") != TARGET_FUNC_QUAL:
            continue
        seq.append(int(m.group("lineno")))
    return tuple(seq)

def extract_invariant(trace_text: str) -> bool:
    segments = _split_segments(trace_text)
    if not segments:
        raise ValueError(
            "No [TRACE][START] markers found -- trace_plugin did not run."
        )
    if len(segments) < 15:
        raise ValueError(
            f"Expected >= 15 test segments; found {len(segments)}."
        )
    sequences = []
    for idx, seg in enumerate(segments, 1):
        s = _extract_sequence(seg)
        if not s:
            raise ValueError(
                f"No event=line entries for {TARGET_FUNC_QUAL!r} in "
                f"segment {idx} -- did the test invoke the target?"
            )
        sequences.append(s)
    return len(sequences) == len(segments) and len(set(sequences)) == 1

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
    invariant_exists = extract_invariant(trace_text)

    qa = {
        "question_kind": "determinism_flakiness",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestTransformWalkRandomForEachPathDeterminismQA`. The "
            "class contains 15 syntactically-identical test methods "
            "(`test_transform_walk_random_foreach_path_determinism_case_01` "
            "through `..._case_15`). Each method instantiates "
            "`cfnlint.template.Template(\"foo.yaml\", _TEMPLATE, "
            "[\"us-east-1\"])` and calls "
            "`_Transform().transform(cfn)` exactly ONCE with the "
            "SAME `_TEMPLATE`. `_TEMPLATE` is an "
            "`AWS::LanguageExtensions` template with an "
            "`Fn::ForEach::L` whose collection is a list of TWO "
            "Refs (`{\"Ref\": \"UnresolvableParam\"}` and "
            "`{\"Ref\": \"AnotherUnresolvableParam\"}`) to "
            "Parameter names that are NOT declared in "
            "`_TEMPLATE[\"Parameters\"]` (which is `{}`). The body "
            "produces `{\"Bucket${L}\": {\"Type\": \"AWS::S3::Bucket\"}}`. "
            "The 15 methods run sequentially within the SAME "
            "pytest process, with no explicit reset of Python's "
            "`random` module state between calls. "
            "QUESTION: do all 15 sequential executions follow the "
            "EXACT SAME sequence of executed line numbers across "
            "ALL FRAMES of "
            "`cfnlint.template.transforms._language_extensions._Transform._walk` "
            "(the recursive workhorse called by `transform`)? "
            "Return JSON with exactly one key: "
            "`{\"invariant_exists\": <bool>}`. "
            "Reasoning rules to simulate: "
            "(1) `_Transform.transform(cfn)` returns "
            "`([], self._walk(cfn.template, {}, cfn))` (line 108 of "
            "`_language_extensions.py`). "
            "(2) `_walk` recurses through the template. For the "
            "`Fn::ForEach::L` key it constructs `_ForEach(...)` "
            "and iterates `foreach.items(cfn, params)` -- which "
            "delegates to `_ForEachCollection.values`. "
            "(3) For each Ref in the collection list, "
            "`_ForEachValueRef.value` raises `_ResolveError` (the "
            "Ref's parameter is undeclared); "
            "`_ForEachCollection.values` catches at line 560 and "
            "substitutes `v = \"\".join(random.choices(string.ascii_letters, "
            "k=_N))` with `_N=7`. The yielded random `v` becomes "
            "the value of the ForEach identifier `${L}` and is "
            "substituted into the body's Resource key via "
            "`_replace_string_params`. "
            "(4) Although the random `v` differs every call, it is "
            "used ONLY as: (a) a string substitution into the "
            "Resource key (`Bucket${L}` -> `Bucket<random>`); "
            "(b) a parameter dict value passed to deeper `_walk` "
            "frames. It NEVER appears in any conditional inside "
            "`_walk` (the `re.match(FUNCTION_FOR_EACH, k)` at line "
            "124 and the `elif k == ...` chain at lines 141-184 "
            "compare against fixed strings like `Fn::ToJsonString`, "
            "`Fn::GetAtt`, etc., none of which `Bucket<7-letters>` "
            "matches). So every iteration of every `_walk` frame "
            "takes the SAME branch on every call. "
            "(5) Python 3.7+ preserves dict insertion order, so the "
            "deepcopied dict at line 122 of `_walk` iterates keys "
            "in the same order each call. "
            "(6) Each test method instantiates a FRESH "
            "`_Transform()`, so the instance-level `_collections` "
            "cache starts empty every call -- no cross-call cache "
            "mutation can divert the path. "
            "(7) The `_ACCOUNT_ID` module-global is never touched "
            "(no `Ref: AWS::AccountId` in the template), so its "
            "state is irrelevant. "
            "(8) Therefore, across the 15 calls, the line-number "
            "sequence visited within all `_walk` frames is "
            "identical -- path-determinism HOLDS even though the "
            "transform's RETURN VALUE differs every time."
        ),
        "template_answer": {
            "invariant_exists": "bool",
        },
        "oracle_answer": {
            "invariant_exists": invariant_exists,
        },
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["line"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestTransformWalkRandomForEachPathDeterminismQA"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
