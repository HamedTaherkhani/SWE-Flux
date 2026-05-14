#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/telegram/_messageentity\.py):(?P<lineno>\d+) "
    r"(?P<func>telegram\._messageentity\.MessageEntity\.concatenate) "
    r"event=return retval=(?P<retval>.*?) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

ENTITY_RE = re.compile(
    r"MessageEntity\(length=(?P<length>\d+), offset=(?P<offset>\d+), "
    r"type=<MessageEntityType\.(?P<type>[A-Z_]+)>\)"
)


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find MessageEntity.concatenate return events in trace log.")

    retval = matches[-1].group("retval")
    retval_match = re.match(r"^\((?P<text>'.*?'), \[(?P<entities>.*)\]\)$", retval)
    if retval_match is None:
        raise ValueError("Could not parse concatenate return tuple from trace retval.")

    output_text = ast.literal_eval(retval_match.group("text"))
    if not isinstance(output_text, str):
        raise ValueError("Parsed output_text is not a string.")

    entities_blob = retval_match.group("entities")
    output_entities = []
    for entity_match in ENTITY_RE.finditer(entities_blob):
        output_entities.append(
            {
                "type": entity_match.group("type"),
                "offset": int(entity_match.group("offset")),
                "length": int(entity_match.group("length")),
            }
        )

    if not output_entities:
        raise ValueError("No entities parsed from concatenate return value.")

    return {
        "output_text": output_text,
        "output_entities": output_entities,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/messageentity_concatenate_direct_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/messageentity_concatenate_direct_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "C4_ProgramState",
        "question": (
            "Use `tests/qa/messageentity_concatenate_direct_output_test.py`, class "
            "`TestMessageEntityConcatenateDirectOutputQA`, method "
            "`test_concatenate_direct_output_case`. "
            "This test directly calls `telegram/_messageentity.py::MessageEntity.concatenate` "
            "(line 286) with three tuples: "
            "`first=('prefix alpha beta | ', [BOLD(7,5), ITALIC(13,4)], True)`, "
            "`second=('core block', [CODE(0,4)], False)`, "
            "`third=(' | suffix zone', [UNDERLINE(3,6)])`. "
            "Inside `concatenate`, `output_text` and `output_entities` are updated in lines 354-355, "
            "and line 357 returns `(output_text, output_entities)`. "
            "What is the exact returned value at line 357? Return it as "
            "`{output_text: str, output_entities: list[{type: str, offset: int, length: int}]}` "
            "with entity order preserved."
        ),
        "template_answer": {
            "output_text": "str",
            "output_entities": "list[{type: str, offset: int, length: int}]",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
