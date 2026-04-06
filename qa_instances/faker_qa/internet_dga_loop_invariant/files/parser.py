import argparse
import json
from pathlib import Path
import re

def parse_trace(trace_log_path: str, out_json_path: str):
    trace_path = Path(trace_log_path)
    if not trace_path.exists():
        raise FileNotFoundError(f"Trace log not found at {trace_log_path}")

    # Regex to capture local variables at the invariant loop iteration line.
    line_pattern = re.compile(
        r"^.*? (?P<path>.*?):(?P<lineno>\d+) (?P<func>.*?)\s+event=(?P<event>line) locals=(?P<locals>\{.*\})"
    )

    domain_invariant_evals = []

    with open(trace_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = line_pattern.match(line)
            if not match:
                continue

            lineno = int(match.group("lineno"))
            func = match.group("func")
            # We target the dga function in faker.providers.internet.Provider
            # Specifically the loop over the length of the DGA name
            if "Provider.dga" in func and lineno == 359: # Line 359: domain += chr(((year ^ month ^ day) % 25) + 97)
                try:
                    # In earlier lines, length and loop iterator _ are updated or loop starts.
                    # domain size should equal the iteration count.
                    # Instead of parsing everything, lets check if the domain is always composed of lowercase letters (ascii 97-122).
                    locals_str = match.group("locals")
                    # Replace single quotes, handle ellipses if locals are truncated.
                    # Trace output might have Python reprs.
                    locals_str = locals_str.replace("'", '"')
                    try:
                        locals_dict = json.loads(locals_str)
                    except json.JSONDecodeError:
                        # Fallback parsing if JSON load fails due to Python specifics (e.g. set or objects)
                        continue
                    
                    if "domain" in locals_dict:
                         domain_val = locals_dict["domain"]
                         # The new character will be added at line 359. So domain at this line has length = iteration index
                         # Is domain ALWAYS composed of lowercase english alphabet? Yes.
                         if len(domain_val) > 0: # Check if string is only lowercase a-z
                             is_lower = domain_val.islower() and domain_val.isalpha()
                             domain_invariant_evals.append(is_lower)
                except Exception as e:
                    print(f"Error parsing locals: {e}")

            # Let's switch to the specific invariant:
            # Does the domain always only contain characters a-z at line 359 (or let's measure final returned values or locals)?
            # Better invariant: `len(domain) <= length` at the end of loop.
            # At line 361 (`return domain + "." + tld`), we can check the size.
            if "Provider.dga" in func and lineno == 361:
                 # at the return statement
                 try:
                    locals_str = match.group("locals")
                    locals_str = locals_str.replace("'", '"')
                    locals_dict = json.loads(locals_str)
                    if "domain" in locals_dict and "length" in locals_dict:
                        # domain should have been appended to `length` times.
                        # so len(domain) == length
                        domain_len = len(locals_dict["domain"])
                        expected_len = locals_dict["length"]
                        domain_invariant_evals.append(domain_len == expected_len)
                 except Exception:
                     pass
                     

    # Evaluate the invariant check
    # Check if for all evaluations, domain_len == expected_len
    # Wait, the question will state: Is `len(domain) == length` an invariant property at line 361?
    invariant_exists = all(domain_invariant_evals) if domain_invariant_evals else False

    oracle_data = {
        "question_kind": "invariant_properties",
        "question": "Use `faker_qa/internet_dga_loop_invariant/files/testcase.py`, class `TestInternetDgaLoopInvariantQA`, method `test_dga_loop_invariant_case`. Focus on function `faker.providers.internet.Provider.dga` in file `faker/providers/internet/__init__.py`. At line `361` (`return domain + \".\" + tld`), consider local variables `domain` and `length`. Across all evaluations of this line during the test suite execution, is the relationship `len(domain) == length` an invariant property? Return JSON as `{\"invariant_exists\": <bool>}` where `true` means invariant holds for every evaluation and `false` means it does not hold.",
        "template_answer": {
             "invariant_exists": "bool"
        },
        "oracle_answer": {
            "invariant_exists": invariant_exists
        }
    }

    out_path = Path(out_json_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(oracle_data, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    parse_trace(args.trace_log, args.out)

