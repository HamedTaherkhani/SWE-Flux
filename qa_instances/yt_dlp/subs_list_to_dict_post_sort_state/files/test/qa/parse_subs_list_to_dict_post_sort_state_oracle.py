#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin emits a per-line `event=line` whose `locals=...` block contains
# only the locals that *changed* since the previous event. Walk events in order
# and accumulate to recover the full snapshot at any point.
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/utils/traversal\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.utils\.traversal\.subs_list_to_dict) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


# Line 376: `for subs in result.values():` -- the FOR statement of the post-sort
# loop. The first hit happens before the loop assigns a value (`subs` is still
# the parameter list at that moment). The K-th subsequent hit (1-indexed K)
# corresponds to the loop-back point AFTER iteration K's `.sort(...)` call has
# completed. So `target_index = TARGET_ITERATION` (in the snapshot list) means
# "after iteration TARGET_ITERATION".
TARGET_FOR_LINE = "376"
TARGET_ITERATION = 1  # state immediately after the first sort call returns


def extract_state(trace_text: str) -> dict:
    cumulative: dict[str, str] = {}
    for_snapshots: list[dict[str, str]] = []

    for m in LINE_RE.finditer(trace_text):
        delta = ast.literal_eval(m.group("locals"))
        cumulative.update(delta)
        if m.group("lineno") == TARGET_FOR_LINE:
            for_snapshots.append(dict(cumulative))

    if not for_snapshots:
        raise ValueError(f"No FOR-line ({TARGET_FOR_LINE}) events found in trace.")

    if len(for_snapshots) <= TARGET_ITERATION:
        raise ValueError(
            f"Need at least {TARGET_ITERATION + 1} FOR events, "
            f"got {len(for_snapshots)}.")

    snap = for_snapshots[TARGET_ITERATION]
    if "result" not in snap:
        raise ValueError(f"`result` not bound at FOR event #{TARGET_ITERATION + 1}: {snap!r}")

    return {
        "result": ast.literal_eval(snap["result"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/subs_list_to_dict_post_sort_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/subs_list_to_dict_post_sort_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    state = extract_state(trace_text)

    qa = {
        "question_kind": "C4_ProgramState",
        "question": (
            "Use `test/qa/subs_list_to_dict_post_sort_state_test.py`, class "
            "`TestSubsListToDictPostSortStateQA`, method "
            "`test_subs_list_to_dict_post_sort_state_case`. "
            "The test calls `yt_dlp.utils.traversal.subs_list_to_dict(subs, ext='vtt')` "
            "(implementation defined at line 342 in `yt_dlp/utils/traversal.py`) with the "
            "exact `SUBS_INPUT` list shown at the top of the test file (deep-copied to "
            "isolate mutation). The function first iterates the input through the "
            "`for sub in subs:` loop at line 359, populating a `defaultdict` named "
            "`result`. After that loop completes, line 374 runs `result = dict(result)`, "
            "and then a second loop at line 376 -- "
            "`for subs in result.values():` -- runs `subs.sort(key=lambda x: "
            "x.pop('quality', 0) or 0)` (line 377) on each list of subs in dict-insertion "
            "order. Note: the lambda **mutates** every element of the iterated list by "
            "popping its `'quality'` key (returning the popped value or 0 if absent), and "
            "the `or 0` clause coerces a popped value of 0 into the sort key 0. "
            "Report the value of the local `result` **immediately after the very first "
            "`subs.sort(...)` call returns** -- i.e., at the line-376 trace event that "
            "fires once the body of iteration 1 (the sort on the first dict value) has "
            "completed and execution loops back to the FOR statement, and BEFORE iteration "
            "2's body runs. "
            "Return a JSON object with one key `result` whose value is the exact `dict` "
            "value of the local `result` at that moment, byte-for-byte. Preserve dict "
            "**insertion order** for both the outer keys and each inner element's keys. "
            "Lists in `result` for keys whose iteration has not yet executed must still "
            "carry their `'quality'` field; the list for the first key must have "
            "`'quality'` removed from every element and be reordered ascending by the "
            "(now-popped) sort key."
        ),
        "template_answer": {
            "result": {"str": [{"str": "any"}]},
        },
        "oracle_answer": state,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
