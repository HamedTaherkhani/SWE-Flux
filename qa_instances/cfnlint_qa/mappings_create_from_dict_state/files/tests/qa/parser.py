from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

ROOT_DIR = Path("/testbed")
_SRC = ROOT_DIR / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from cfnlint.context._mappings import Map, Mappings, _MappingSecondaryKey

INSTANCE_ID = "mappings_create_from_dict_state"
TARGET_FUNC_QUAL = "cfnlint.context._mappings.Mappings.create_from_dict"

RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=return retval=(?P<retval>.*?) "
    r"locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)

def extract_returned_mappings(trace_text: str):
    matches = [
        m for m in RETURN_RE.finditer(trace_text)
        if m.group("func") == TARGET_FUNC_QUAL
    ]
    if not matches:
        raise ValueError(
            f"No return events for {TARGET_FUNC_QUAL!r} found in the trace log."
        )

    retval_repr = matches[-1].group("retval")
    eval_globals = {
        "__builtins__": {},
        "Mappings": Mappings,
        "Map": Map,
        "_MappingSecondaryKey": _MappingSecondaryKey,
        "True": True,
        "False": False,
        "None": None,
    }
    obj = eval(retval_repr, eval_globals)
    if not isinstance(obj, Mappings):
        raise ValueError(
            "Expected the parsed retval to be a Mappings instance, got: "
            f"{type(obj).__name__}"
        )
    return obj

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
    obj = extract_returned_mappings(trace_text)
    as_nested_dict = asdict(obj)

    qa = {
        "question_kind": "C4_ProgramState",
        "question": (
            "Use `tests/qa/testcase.py`, class "
            "`TestMappingsCreateFromDictStateQA`, method "
            "`test_mappings_create_from_dict_state_case`. The test "
            "calls "
            "`cfnlint.context._mappings.Mappings.create_from_dict(_INSTANCE)` "
            "(defined at line 25 of "
            "`src/cfnlint/context/_mappings.py`). That classmethod "
            "and its two delegate classmethods "
            "`Map.create_from_dict` (line 87) and "
            "`_MappingSecondaryKey.create_from_dict` (line 59) build "
            "a three-level frozen-dataclass tree from `_INSTANCE` "
            "with the following filtering rules: "
            "(1) at the `Mappings` level, the key `\"Fn::Transform\"` "
            "flips a Mappings-level `is_transform=True` flag and is "
            "dropped, NON-string keys are silently dropped, all other "
            "string keys produce a `Map.create_from_dict(v)` entry; "
            "(2) at the `Map` level, if `v` is NOT a dict, the result "
            "is `Map(keys={}, is_transform=False)`; otherwise "
            "`\"Fn::Transform\"` flips the Map's `is_transform=True` "
            "and is dropped, non-string keys are dropped, all other "
            "string keys produce a `_MappingSecondaryKey.create_from_dict(v)` "
            "entry; "
            "(3) at the `_MappingSecondaryKey` level, "
            "`\"Fn::Transform\"` flips its `is_transform`, and other "
            "entries are kept ONLY if the key is `str` AND the value "
            "isinstance of `(str, list, int, float)`. Note that "
            "`bool` is a subclass of `int` in Python so `True` and "
            "`False` ARE kept; `None`, nested `dict`, and `tuple` "
            "are dropped. Capture the EXACT structure of the "
            "returned `Mappings` dataclass instance. Return the "
            "answer as the field `mappings` whose value is the "
            "nested-dict form produced by `dataclasses.asdict` -- "
            "i.e. `{\"maps\": {<top_key>: {\"keys\": {<sec_key>: "
            "{\"keys\": {<inner_key>: <value>}, "
            "\"is_transform\": <bool>}}, \"is_transform\": <bool>}}, "
            "\"is_transform\": <bool>}`. Preserve dict insertion order."
        ),
        "template_answer": {
            "mappings": {
                "maps": {
                    "<top_key>": {
                        "keys": {
                            "<sec_key>": {
                                "keys": {"<inner_key>": "<value>"},
                                "is_transform": "bool",
                            }
                        },
                        "is_transform": "bool",
                    }
                },
                "is_transform": "bool",
            }
        },
        "oracle_answer": {"mappings": as_nested_dict},
        "execution": {
            "trace_target": TARGET_FUNC_QUAL,
            "trace_events": ["return"],
            "pytest_nodeid": (
                "tests/qa/testcase.py::TestMappingsCreateFromDictStateQA::"
                "test_mappings_create_from_dict_state_case"
            ),
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
