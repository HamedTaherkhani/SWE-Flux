#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Regex pattern to match the line event at line 1196 where options is visible
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (?P<path>/testbed/lib/matplotlib/font_manager\.py):(?P<lineno>1196) "
    r"(?P<func>matplotlib\.font_manager\.(?:FontManager\.)?score_family) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def extract_options_state(trace_text: str) -> dict:
    """Extract the options list state at line 1196 from the trace log."""
    matches = list(LINE_RE.finditer(trace_text))
    if not matches:
        raise ValueError(
            "Could not find matplotlib.font_manager.score_family "
            "line event at line 1196 in trace log."
        )
    
    # Find the first match where options is defined (when family1 is 'serif')
    target_match = None
    for match in matches:
        locals_raw = match.group("locals")
        parsed_locals = ast.literal_eval(locals_raw)
        
        # Check if this is the line where options is in locals
        if "options" in parsed_locals:
            target_match = match
            # We want the first occurrence where options appears
            break
    
    if target_match is None:
        raise ValueError(
            "Could not find the line event at line 1196 where 'options' is defined "
            "for the 'serif' family in the trace log."
        )
    
    locals_raw = target_match.group("locals")
    parsed_locals = ast.literal_eval(locals_raw)
    
    if "options" not in parsed_locals:
        raise ValueError(
            "Line event at line 1196 does not include 'options' in locals."
        )
    
    # Parse the options list from the string representation
    options_str = parsed_locals["options"]
    # The options is a list of strings, parse it
    options = ast.literal_eval(options_str)
    
    return {
        "options": options
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/font_manager_score_family_indirect_options/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/font_manager_score_family_indirect_options/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_options_state(trace_text)

    qa = {
        "question_kind": "S3_ProgramState",
        "question": (
            "Use `tests/qa/font_manager_score_family_indirect_options_test.py`, class "
            "`TestFontManagerScoreFamilyIndirectOptionsQA`, method "
            "`test_font_manager_score_family_indirect_options_case`. "
            "In that test, line 14 defines `families = ['serif', 'DejaVu Sans', 'Arial', 'Times New Roman']`, "
            "and line 26 calls `fm.score_family(families, family2)` directly. "
            "Inside `lib/matplotlib/font_manager.py::FontManager.score_family` (defined at line 1175), "
            "execution enters a for loop at line 1192 (`for i, family1 in enumerate(families)`). "
            "At line 1194, the condition `if family1 in font_family_aliases:` checks whether the current "
            "`family1` is an alias (like 'serif', 'sans-serif', etc.). "
            "When this condition is True (i.e., when `family1 == 'serif'` in the first iteration), "
            "execution reaches line 1195 where `options = [*map(str.lower, self._expand_aliases(family1))]` "
            "is assigned. This line calls `self._expand_aliases('serif')` to get the list of actual font "
            "families mapped to the 'serif' alias, converts them all to lowercase, and stores them in `options`. "
            "What exact list value does the local variable `options` hold at line 1195 when `family1 == 'serif'`?"
        ),
        "template_answer": {
            "options": ["str"]
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
