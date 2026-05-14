import argparse
import ast
import json
from pathlib import Path
import re

LINE_PATTERN = re.compile(
    r"^(?:[0-9\-:\.]+ )?(?P<path>.*?):(?P<lineno>\d+) (?P<func>.*?)\s+event=(?P<event>\w+) locals=(?P<locals>\{.*\})"
)


def parse_trace(trace_log_path: str, out_json_path: str) -> None:
    trace_path = Path(trace_log_path)
    if not trace_path.exists():
        raise FileNotFoundError(f"Trace log not found at {trace_log_path}")

    invariants = []

    with trace_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            match = LINE_PATTERN.match(line.strip())
            if not match:
                continue

            if match.group("event") != "line":
                continue

            if match.group("func").endswith("clabe") and int(match.group("lineno")) in (280, 281):
                locals_repr = match.group("locals")
                try:
                    locals_dict = ast.literal_eval(locals_repr)
                except (SyntaxError, ValueError):
                    continue

                if "result" not in locals_dict:
                    continue

                result_value = locals_dict["result"]
                if not isinstance(result_value, str):
                    invariants.append(False)
                    continue

                normalized = result_value
                if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in ("\"", "'"):
                    normalized = normalized[1:-1]

                invariants.append(len(normalized) == 17 and normalized.isdigit())

    invariant_exists = bool(invariants) and all(invariants)

    oracle_data = {
        "question_kind": "M7_Invariants",
        "question": "Use `faker_qa/bank_es_mx_clabe_result_shape_invariant/files/testcase.py`, class `TestBankClabeResultShapeInvariantQA`, method `test_clabe_result_shape_invariant`. Focus on function `faker.providers.bank.es_MX.Provider.clabe` in file `faker/providers/bank/es_MX/__init__.py`. At line `280` (`result = f\"{bank:03d}{city:03d}{branch:04d}{account:07d}\"`), consider local variable `result`. Is the shape (a 17-character string composed only of digits) of `result` an invariant property across every execution that the test method triggers? Return JSON as `{\"invariant_exists\": <bool>}` where `true` means the property holds for every evaluation and `false` means it does not hold.",
        "template_answer": {
            "invariant_exists": "bool"
        },
        "oracle_answer": {
            "invariant_exists": invariant_exists
        }
    }

    out_path = Path(out_json_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(oracle_data, fh, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    parse_trace(args.trace_log, args.out)
