from __future__ import annotations

import argparse
import json
from pathlib import Path


QUESTION = (
    "Use `tests/qa/state_process_event_generator_direct_output_test.py`, class "
    "`TestStateProcessEventGeneratorDirectOutputQA`, method "
    "`test_state_process_event_generator_direct_output_case`. The test directly "
    "calls `state._process_event(...)` at "
    "`tests/qa/state_process_event_generator_direct_output_test.py:105`; the "
    "target method is `reflex.state.BaseState._process_event`, defined at "
    "`reflex/state.py:1737`. In the target, local variable `fn` is assigned at "
    "`reflex/state.py:1756`, `type_hints` is assigned at lines 1758-1761, the "
    "input `payload` is mutated/coerced in the loop at lines 1763-1807, regular "
    "generator output is detected at line 1825, yielded values are converted to "
    "`StateUpdate` objects at lines 1826-1838, and exception fallback would run "
    "at lines 1845-1856. The test state variables `count`, `tags_seen`, "
    "`pair_total`, and `history` are declared at "
    "`tests/qa/state_process_event_generator_direct_output_test.py:24-27`; "
    "computed vars `score` and `status` are defined at lines 29-35. The generator "
    "handler `complex_generator` is defined at lines 40-62; it mutates `count`, "
    "`tags_seen`, `pair_total`, and `history`, yields event specs at line 51 "
    "and lines 55-58, and returns a final event spec at line 62. The payload passed to "
    "the target is created at lines 97-102 and starts with `amount` as a string, "
    "`tags` as a list, `pair` as a list, and `payload` as a dict. What is the "
    "exact direct output of this `_process_event` call, summarized as the "
    "post-call coerced payload, the ordered list of yielded `StateUpdate`s, and "
    "the final state snapshot? Return exactly the keys `coerced_payload_after_call`, "
    "`updates`, and `final_state`."
)


TEMPLATE_ANSWER = {
    "coerced_payload_after_call": {
        "amount": "int",
        "tags": ["str"],
        "pair": ["int"],
        "payload_type": "str",
        "payload_dict": {"str": "int | str"},
    },
    "updates": [
        {
            "delta": {"str": {"str": "int | str | list"}},
            "events": [
                {
                    "token": "str",
                    "name": "str",
                    "payload": {"str": "int | str | null"},
                    "router_data": {"str": "int | str | dict"},
                }
            ],
            "final": "bool",
        }
    ],
    "final_state": {
        "count": "int",
        "tags_seen": ["str"],
        "pair_total": "int",
        "history": ["str"],
        "score": "int",
        "status": "str",
        "dirty_vars": ["str"],
    },
}


def extract_result(pytest_log: Path) -> dict:
    for line in pytest_log.read_text(encoding="utf-8").splitlines():
        if "QA_RESULT_JSON=" in line:
            return json.loads(line.split("QA_RESULT_JSON=", 1)[1])
    raise RuntimeError(f"QA_RESULT_JSON marker not found in {pytest_log}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pytest-log", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    oracle_answer = extract_result(Path(args.pytest_log))
    oracle = {
        "question_kind": "program_state_prediction",
        "question": QUESTION,
        "template_answer": TEMPLATE_ANSWER,
        "oracle_answer": oracle_answer,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(oracle, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps(oracle, indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
