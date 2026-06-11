#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path
TARGET="pybamm.meshes.meshes.Mesh.__init__"; PREFIX="pybamm.meshes."; RE=re.compile(r"^.*? (?P<func>\S+) event=(?P<event>call|return|exception)\b(?: exc=(?P<kind>[A-Za-z_]\w*):)?")
def extract(lines):
    depth=top=0;kinds=set()
    for line in lines:
        m=RE.match(line)
        if not m: continue
        f,e,k=m.group("func","event","kind")
        if e=="call" and f==TARGET:
            if depth==0: top+=1
            depth+=1;continue
        if depth and e=="exception" and f.startswith(PREFIX) and k: kinds.add(k)
        if depth and e=="return" and f==TARGET: depth-=1
    if top!=10 or depth: raise ValueError(f"Expected 10 complete top-level target calls, found {top}, depth={depth}")
    return {"exception_types":sorted(kinds)}
def main():
    p=argparse.ArgumentParser();p.add_argument("--trace-log",required=True);p.add_argument("--out",required=True);a=p.parse_args()
    q="Run `tests/qa/mesh_init_exception_diversity_suite_test.py` methods `test_case_01` through `test_case_10` in `TestMeshInitExceptionDiversityQA`, executed sequentially in file order. Each test calls `_mesh` once, which makes exactly one top-level call to `pybamm.meshes.meshes.Mesh.__init__` and generically catches any exception that escapes it, so all tests pass. Geometry, submesh-type, and point-count preparation before `_mesh` is outside the target dynamic extent. Across the dynamic extent from each top-level `Mesh.__init__` call until its matching return, including nested calls, identify every concrete exception class for which a Python `exception` trace event occurs. Include exceptions caught internally by PyBaMM and exceptions that escape the target and are caught by `_mesh`. Consider only frames whose source file is under `src/pybamm` and whose trace name starts with `pybamm.meshes.`. Ignore pytest and test-helper frames. Which exception kinds are encountered? Return `exception_types` as unique class names sorted lexicographically."
    qa={"question_kind":"M5_ExceptionalBehavior","question":q,"template_answer":{"exception_types":["str"]},"oracle_answer":extract(Path(a.trace_log).open())};Path(a.out).write_text(json.dumps(qa,indent=2)+"\n");print(json.dumps(qa,indent=2))
if __name__=="__main__":main()
