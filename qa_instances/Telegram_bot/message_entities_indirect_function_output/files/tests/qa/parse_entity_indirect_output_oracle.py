#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/_utils/entities\.py):(?P<lineno>\d+) "
    r"(?P<func>telegram\._utils\.entities\.parse_message_entity) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> str:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find parse_message_entity return events in trace log.")

    code_matches = [m for m in matches if "MessageEntityType.CODE" in m.group("locals")]
    target = code_matches[-1] if code_matches else matches[-1]

    retval = target.group("retval")
    parsed = ast.literal_eval(retval)
    if not isinstance(parsed, str):
        raise ValueError("Parsed return value is not a string.")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/message_entities_indirect_function_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/message_entities_indirect_function_output/oracle.json",
    )
    args = parser.parse_args()

    trace_log = Path(args.trace_log).read_text(encoding="utf-8")
    entity_text = extract_output(trace_log)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `tests/qa/entity_indirect_output_case_test.py`, class "
            "`TestEntityIndirectOutputQA`, method `test_indirect_target_output_case`. "
            "The method builds a `Message` with text formed as `prefix + base_text`, where "
            "`prefix='§🚀'` and `base_text='A👩‍💻B𠌕C𝄢D🙂E'`. It defines `base_entities` with "
            "`MessageEntity(type=MessageEntity.BOLD, offset=1, length=5)` and "
            "`MessageEntity(type=MessageEntity.CODE, offset=4, length=8)`, then shifts them via "
            "`MessageEntity.shift_entities(prefix, base_entities)`, and finally calls "
            "`message.parse_entities(types=[MessageEntity.CODE, MessageEntity.BOLD])` at "
            "`telegram/_message.py:4603`. This goes through "
            "`telegram/_utils/entities.py:72` into "
            "`telegram/_utils/entities.py::parse_message_entity` (line 33). "
            "Inside that function, the local variable `entity_text` is reassigned at line 44 "
            "after UTF-16 slicing, and line 46 returns `entity_text.decode(TextEncoding.UTF_16_LE)`. "
            "For the call where `entity.type == MessageEntity.CODE`, what is the exact returned "
            "string at line 46 (equivalently, the decoded value of `entity_text` from line 44)?"
        ),
        "template_answer": {"entity_text": "str"},
        "oracle_answer": {"entity_text": entity_text},
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
