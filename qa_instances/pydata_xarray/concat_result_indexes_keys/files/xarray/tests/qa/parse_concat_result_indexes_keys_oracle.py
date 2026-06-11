#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>[^ ]+) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _extract_top_level_dict_keys(raw_dict_repr: str) -> list[str]:
    text = raw_dict_repr.strip()
    if not (text.startswith("{") and text.endswith("}")):
        raise ValueError("Expected a dict repr string.")

    keys: list[str] = []
    i = 0
    n = len(text)
    depth = 0
    in_string = False
    quote = ""
    escape = False

    while i < n:
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_string = False
            i += 1
            continue

        if ch in ("'", '"'):
            # Potential top-level key string: must be at depth 1.
            if depth == 1:
                quote = ch
                j = i + 1
                buf = []
                esc2 = False
                while j < n:
                    cj = text[j]
                    if esc2:
                        buf.append(cj)
                        esc2 = False
                    elif cj == "\\":
                        esc2 = True
                    elif cj == quote:
                        break
                    else:
                        buf.append(cj)
                    j += 1
                if j >= n:
                    raise ValueError("Unterminated string while parsing dict key.")
                key = "".join(buf)

                k = j + 1
                while k < n and text[k].isspace():
                    k += 1
                if k < n and text[k] == ":":
                    keys.append(key)
                i = j + 1
                continue

            in_string = True
            quote = ch
            i += 1
            continue

        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
        i += 1

    return keys


def extract_result_indexes_keys(trace_text: str) -> dict[str, list[str]]:
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError("Could not find _dataset_concat line events in trace log.")

    for match in matches:
        func = match.group("func")
        if not func.endswith("._dataset_concat"):
            continue

        locals_map = ast.literal_eval(match.group("locals"))
        if not isinstance(locals_map, dict):
            continue
        if "result_indexes" not in locals_map:
            continue

        # Use the first trace snapshot where `result_indexes` becomes non-empty.
        keys = _extract_top_level_dict_keys(locals_map["result_indexes"])
        if keys:
            return {"result_indexes_keys": sorted(set(keys))}

    raise ValueError("Could not extract non-empty result_indexes keys from trace.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/concat_result_indexes_keys/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/concat_result_indexes_keys/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_result_indexes_keys(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `xarray/tests/qa/concat_result_indexes_keys_test.py`, class "
            "`TestConcatResultIndexesKeysHardQA`, method "
            "`test_concat_result_indexes_keys_case`. "
            "At line 41, `xr.concat(...)` is called with `dim=pd.Index(['b0','b1','b2'], name='batch')`, "
            "which executes `xarray/core/concat.py::_dataset_concat`. "
            "Inside `_dataset_concat`, consider the first trace snapshot in that function where local "
            "variable `result_indexes` is non-empty. What top-level dictionary keys does `result_indexes` "
            "hold in that first non-empty snapshot? "
            "Return them in sorted ascending order as `result_indexes_keys`."
        ),
        "template_answer": {
            "result_indexes_keys": "list[str]"
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
