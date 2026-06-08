#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? /testbed/telegram/_files/inputfile\.py:(?P<lineno>\d+) "
    r"telegram\._files\.inputfile\.InputFile\.field_tuple event=return "
    r"retval=(?P<retval>\(.*\)) locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_output(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find InputFile.field_tuple return event.")

    retval = ast.literal_eval(matches[-1].group("retval"))
    if not isinstance(retval, tuple) or len(retval) != 3:
        raise ValueError("Unexpected return format for InputFile.field_tuple.")

    return {
        "filename": retval[0],
        "input_file_content": retval[1],
        "mimetype": retval[2],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/inputfile_incompatible_type_output/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/inputfile_incompatible_type_output/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S6_Exceptions",
        "question": (
            "Use `tests/qa/inputfile_incompatible_type_output_test.py`, class "
            "`TestInputFileIncompatibleTypeOutputQA`, method "
            "`test_inputfile_incompatible_type_output_case`. "
            "At line 9, variable `incompatible_obj` is constructed and passed as "
            "`obj=incompatible_obj` at line 12 to `telegram/_files/inputfile.py:96::InputFile.__init__`, "
            "even though `obj` is not one of the expected input types. "
            "At line 13, variable `field_tuple` reads "
            "`telegram/_files/inputfile.py:129::InputFile.field_tuple`. "
            "What is the exact output value of `field_tuple` for this execution?"
        ),
        "template_answer": {
            "filename": "str",
            "input_file_content": "int",
            "mimetype": "str",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
