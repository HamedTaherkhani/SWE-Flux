#!/usr/bin/env python3
import argparse,json,re,xml.etree.ElementTree as ET
from pathlib import Path
CLASS="TestInterpolantInitExceptionRegionQA"; RX=re.compile(r"test_case_(\d{2})$"); ER=re.compile(r"(?:^|[.\s])(?P<kind>ValueError|TypeError)(?=:)")
def extract(path):
 o={}
 for c in ET.parse(path).iter("testcase"):
  n=c.attrib.get("name","")
  if not RX.fullmatch(n) or c.attrib.get("classname","").split(".")[-1]!=CLASS:continue
  f=list(c.findall("failure"))+list(c.findall("error"))
  if not f:o[n]=None
  else:
   k=ER.findall(f"{f[0].attrib.get('message','')}\n{f[0].text or ''}")
   if len(f)!=1 or not k:raise ValueError(f"Cannot identify exception for {n}")
   o[n]=k[-1]
 e=[f"test_case_{i:02d}" for i in range(1,11)]
 if sorted(o)!=e:raise ValueError("Missing tests")
 return {"safe_tests":[t for t in e if o[t] is None],"crashing_tests":[{"test":t,"exception_type":o[t]} for t in e if o[t] is not None]}
def main():
 p=argparse.ArgumentParser();p.add_argument("--report");p.add_argument("--out");a=p.parse_args()
 q="Run `tests/qa/interpolant_init_exception_region_suite_test.py` methods `test_case_01` through `test_case_10` in `TestInterpolantInitExceptionRegionQA`, executed sequentially in file order. Each test calls `_construct` once, which calls `pybamm.expression_tree.interpolant.Interpolant.__init__` exactly once. Classify a test as crashing only when an exception escapes that constructor call; classify it as safe when the call returns normally. For each crashing test, report the concrete escaping exception class name. Ignore pytest framework activity and the assertion after successful construction. In both answer fields, identify tests only by their exact bare method names, for example `test_case_01`; do not use ordinal labels, class-qualified names, file paths, or pytest node IDs. Which tests are safe and which crash? Return `safe_tests` in file order and `crashing_tests` in file order, with each crashing entry containing `test` and `exception_type`."
 d={"question_kind":"M5_ExceptionalBehavior","question":q,"template_answer":{"safe_tests":["str"],"crashing_tests":[{"test":"str","exception_type":"str"}]},"oracle_answer":extract(a.report)};Path(a.out).write_text(json.dumps(d,indent=2)+"\n");print(json.dumps(d,indent=2))
if __name__=="__main__":main()
