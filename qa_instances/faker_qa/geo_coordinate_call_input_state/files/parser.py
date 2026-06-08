#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CALL_LINE_RE = re.compile(r"'center': '([^']*)'.*?'radius': '([^']*)'")

TARGET_CALL_INDEX = 2


def _parse_local_scalar(s: str):
    if s == "None":
        return None
    try:
        if "." in s or "e" in s.lower():
            return float(s)
        return int(s)
    except ValueError:
        return s


def extract_output(trace_text: str) -> dict[str, object | None]:
    lines = []
    for line in trace_text.splitlines():
        if "faker.providers.geo.coordinate" not in line:
            continue
        if " event=call " not in line:
            continue
        lines.append(line)

    if len(lines) < TARGET_CALL_INDEX:
        raise ValueError(
            f"Expected at least {TARGET_CALL_INDEX} coordinate call events, found {len(lines)}.",
        )

    target = lines[TARGET_CALL_INDEX - 1]
    m = CALL_LINE_RE.search(target)
    if not m:
        raise ValueError(f"Could not parse center/radius from call line: {target!r}")

    return {
        "center": _parse_local_scalar(m.group(1)),
        "radius": _parse_local_scalar(m.group(2)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/faker_qa/geo_coordinate_call_input_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/faker_qa/geo_coordinate_call_input_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    execution = (
        "from faker import Faker\n"
        "fake = Faker()\n"
        "fake.seed_instance(999001)\n"
        "fake.longitude()\n"
        "fake.location_on_land()\n"
        "fake.local_latlng('DE')\n"
        "fake.local_latlng('FR', coords_only=True)\n"
        "fake.coordinate(center=-12.375, radius=0.75)\n"
        "fake.latlng()\n"
    )

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `faker_qa/geo_coordinate_call_input_state/files/testcase.py`, class "
            "`TestGeoCoordinateCallInputStateQA`, method `test_geo_coordinate_call_input_state_case`. "
            "In that test, line 11 constructs `Faker()`, line 12 calls `seed_instance(999001)`, line 13 calls "
            "`longitude()`, line 14 calls `location_on_land()`, line 15 calls `local_latlng('DE')`, line 16 "
            "calls `local_latlng('FR', coords_only=True)`, line 17 calls "
            "`coordinate(center=-12.375, radius=0.75)`, and line 18 calls `latlng()`. `location_on_land` and "
            "`local_latlng` filter `land_coords` and "
            "use `random_element` but do **not** call `coordinate`. `latlng` composes `latitude()` and "
            "`longitude()`, each of which calls `coordinate()` with default arguments. This is a "
            "**Function/Method Input States** task: at the **second** chronological `call` event for "
            "`faker/providers/geo/__init__.py::Provider.coordinate` (defined at line 1005) during this run, "
            "what are the exact runtime values bound to parameters `center` and `radius` (use Python "
            "`None` for a missing center, and floating-point values where applicable)?"
        ),
        "template_answer": {
            "center": "null | float | int",
            "radius": "float | int",
        },
        "oracle_answer": output,
        "execution": execution,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
