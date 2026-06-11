#!/usr/bin/env python3
import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

CLASS_NAME = "TestBatteryModelOptionsExceptionRegionQA"
CASE_RE = re.compile(r"test_case_(\d{2})$")
EXCEPTION_RE = re.compile(
    r"(?:^|[.\s])(?P<kind>OptionError|NotImplementedError)(?=:)"
)


def extract(report):
    outcomes = {}
    for case in ET.parse(report).iter("testcase"):
        name = case.attrib.get("name", "")
        match = CASE_RE.fullmatch(name)
        if not match or case.attrib.get("classname", "").split(".")[-1] != CLASS_NAME:
            continue
        test_id = name
        failures = list(case.findall("failure")) + list(case.findall("error"))
        if not failures:
            outcomes[test_id] = None
            continue
        if len(failures) != 1:
            raise ValueError(f"Expected one escaping exception for {test_id}")
        failure = failures[0]
        details = f"{failure.attrib.get('message', '')}\n{failure.text or ''}"
        kinds = EXCEPTION_RE.findall(details)
        if not kinds:
            raise ValueError(f"Could not identify exception type for {test_id}")
        outcomes[test_id] = kinds[-1]

    expected = [f"test_case_{index:02d}" for index in range(1, 11)]
    if sorted(outcomes) != expected:
        raise ValueError(f"Expected {expected}, found {sorted(outcomes)}")

    return {
        "safe_tests": [test for test in expected if outcomes[test] is None],
        "crashing_tests": [
            {"test": test, "exception_type": outcomes[test]}
            for test in expected
            if outcomes[test] is not None
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    qa = {
        "question_kind": "M5_ExceptionalBehavior",
        "question": (
            "Run `tests/qa/battery_model_options_exception_region_suite_test.py` "
            "methods `test_case_01` through `test_case_10` in "
            "`TestBatteryModelOptionsExceptionRegionQA`, executed sequentially in file "
            "order. Each test calls `_construct` once, which calls "
            "`pybamm.models.full_battery_models.base_battery_model.BatteryModelOptions` "
            "exactly once. Classify a test as crashing only when an exception escapes "
            "that `BatteryModelOptions(...)` call; classify it as safe when the call "
            "returns normally. For each crashing test, report the concrete escaping "
            "exception class name. Ignore pytest framework activity and the assertions "
            "after a successful construction. In both answer fields, identify tests only by their exact bare method names, for example `test_case_01`; do not use ordinal labels, class-qualified names, file paths, or pytest node IDs. Which tests are safe and which crash? "
            "Return `safe_tests` in file order and `crashing_tests` in file order, with "
            "each crashing entry containing `test` and `exception_type`."
        ),
        "template_answer": {
            "safe_tests": ["str"],
            "crashing_tests": [{"test": "str", "exception_type": "str"}],
        },
        "oracle_answer": extract(args.report),
    }
    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
