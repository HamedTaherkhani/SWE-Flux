from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INSTANCE_ID = "transform_random_foreach_output_determinism"
TARGET_FUNC_QUAL = (
    "cfnlint.template.transforms._language_extensions._Transform.transform"
)

START_MARKER_RE = re.compile(r"\[TRACE\]\[START\]", re.MULTILINE)
RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=return retval=(?P<retval>.*?) locals=\{",
    re.MULTILINE,
)

def _split_segments(trace_text: str) -> list[str]:
    parts = START_MARKER_RE.split(trace_text)
    return [p for p in parts[1:] if p.strip()]

def _extract_retval(segment: str) -> str | None:
    for m in RETURN_RE.finditer(segment):
        if m.group("func") != TARGET_FUNC_QUAL:
            continue
        return m.group("retval")
    return None

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
    retvals = []
    for idx, seg in enumerate(segments, 1):
        rv = _extract_retval(seg)
        if rv is None:
            raise ValueError(
                f"No event=return for {TARGET_FUNC_QUAL!r} in segment {idx}."
            )
        retvals.append(rv)
    return len(retvals) == len(segments) and len(set(retvals)) == 1

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
            "`TestTransformRandomForEachOutputDeterminismQA`. The "
            "class contains 15 syntactically-identical test methods "
            "(`test_transform_random_foreach_output_determinism_case_01` "
            "through `..._case_15`). Each method instantiates "
            "`cfnlint.template.Template(\"foo.yaml\", _TEMPLATE, "
            "[\"us-east-1\"])` and calls "
            "`cfnlint.template.transforms._language_extensions._Transform()"
            ".transform(cfn)` exactly ONCE with the SAME `_TEMPLATE`. "
            "`_TEMPLATE` is an `AWS::LanguageExtensions` template "
            "with an `Fn::ForEach::L` whose collection is a list of "
            "TWO Refs (`{\"Ref\": \"UnresolvableParam\"}` and "
            "`{\"Ref\": \"AnotherUnresolvableParam\"}`) to Parameter "
            "names that are NOT declared in `_TEMPLATE[\"Parameters\"]` "
            "(which is `{}`). The body produces "
            "`{\"Bucket${L}\": {\"Type\": \"AWS::S3::Bucket\"}}`. "
            "The 15 methods run sequentially within the SAME pytest "
            "process, with no explicit reset of Python's `random` "
            "module state between calls. "
            "QUESTION: is the value returned by "
            "`_Transform.transform(cfn)` IDENTICAL across all 15 "
            "sequential executions? Return JSON with exactly one "
            "key: `{\"invariant_exists\": <bool>}`. "
            "Reasoning rules to simulate: "
            "(1) `_Transform.transform(cfn)` returns "
            "`([], self._walk(cfn.template, {}, cfn))` (line 108 of "
            "`_language_extensions.py`). The `_walk` result is a "
            "deepcopied dict mirroring the template's structure with "
            "Fn::ForEach expanded. "
            "(2) `_walk` dispatches the `Fn::ForEach::L` key (line "
            "124-140), constructs `_ForEach(k, v, self._collections)`, "
            "and iterates `foreach.items(cfn, params)` (line 128). "
            "(3) `_ForEach.items` delegates to `_ForEachCollection"
            ".values(cfn, ...)`. With a literal-list collection, "
            "the latter iterates `self._collection` (each item being "
            "a `_ForEachValueRef` for one of the Refs). "
            "(4) For each item, `_ForEachCollection.values` does "
            "`yield item.value(cfn, {}, False)` (line 559). With "
            "`Ref`-to-undeclared-Parameter, "
            "`_ForEachValueRef.value` falls through line 511-513 "
            "(`p = cfn.template.get(\"Parameters\", {}).get(v); "
            "if not p: raise _ResolveError`). "
            "(5) `_ForEachCollection.values` catches the "
            "`_ResolveError` at line 560 and substitutes "
            "`v = \"\".join(random.choices(string.ascii_letters, "
            "k=_N))` (where `_N=7`). The yielded `v` is then used "
            "as the value of `${L}`, and `_walk` substitutes it into "
            "the Resource key via `_replace_string_params`. "
            "(6) Python's `random` module is seeded from system "
            "entropy at process start AND advances state with every "
            "`random.choices` call, so subsequent calls produce "
            "DIFFERENT random outputs. The 15 sequential transform "
            "calls within ONE process therefore embed 15 different "
            "pairs of random 7-letter suffixes into the Resource "
            "keys. "
            "(7) Hence `_Transform.transform(cfn)`'s return value "
            "(which contains those Resource keys) differs across "
            "the 15 runs."
        ),
        "template_answer": {
            "invariant_exists": "bool",
        },
        "oracle_answer": {
            "invariant_exists": invariant_exists,
        },
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["return"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestTransformRandomForEachOutputDeterminismQA"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
