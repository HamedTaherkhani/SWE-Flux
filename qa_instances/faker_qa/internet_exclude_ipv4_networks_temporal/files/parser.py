import argparse
import json
import os
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-log", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    if not os.path.exists(args.trace_log):
        print("Trace log not found")
        sys.exit(1)

    with open(args.trace_log, "r") as f:
        lines = f.readlines()

    networks_history = []
    
    for line in lines:
        line = line.strip()
        if "event=line" not in line and "event=call" not in line:
            continue
        
        locals_idx = line.find("locals=")
        if locals_idx == -1:
            continue
            
        locals_str = line[locals_idx + 7:]
        try:
            import ast
            locs = ast.literal_eval(locals_str)
            if "networks" in locs:
                val_str = locs["networks"]
                if not networks_history or networks_history[-1] != val_str:
                    networks_history.append(val_str)
        except Exception as e:
            pass

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `testcase.py`, class `TestInternetExcludeIpv4NetworksQA`, method "
            "`test_internet_exclude_ipv4_networks_case`. Focus only on function "
            "`faker.providers.internet.Provider._exclude_ipv4_networks` in file "
            "`faker/providers/internet/__init__.py`. Track exactly the variable: `networks`. "
            "List the ordered sequence of all values assigned to this variable during the "
            "execution of this test. Return the answer as `temporal_value_history`, a list "
            "of strings representing the stringified values of the variable in chronological "
            "assignment order."
        ),
        "template_answer": {
            "temporal_value_history": ["str"]
        },
        "oracle_answer": {
            "temporal_value_history": networks_history
        }
    }

    with open(args.out, "w") as f:
        json.dump(qa, f, indent=2)

if __name__ == "__main__":
    main()
