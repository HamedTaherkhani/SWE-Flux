#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


def _parse_call_trace_line(line: str) -> dict[str, str] | None:
    line = line.strip()
    if "event=call" not in line:
        return None
    m_ts = re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+\s+", line)
    if m_ts:
        line = line[m_ts.end() :]
    marker = " event=call locals="
    mi = line.find(marker)
    if mi < 0:
        return None
    head, rest = line[:mi], line[mi + len(marker) :]
    head_parts = head.rsplit(" ", 1)
    if len(head_parts) != 2:
        return None
    path_lineno, func = head_parts
    path, _, lineno = path_lineno.rpartition(":")
    if not path or not lineno.isdigit():
        return None
    return {"path": path, "lineno": lineno, "func": func, "locals": rest}


def _locals_dict_from_trace(locals_blob: str) -> dict | None:
    """Parse traced locals=… dict; tolerate repr that breaks literal_eval."""
    try:
        loc = ast.literal_eval(locals_blob)
        if isinstance(loc, dict):
            return loc
    except (SyntaxError, ValueError):
        pass
    return None


def _bbox_from_locals_blob(blob: str):
    """Extract bbox argument from a locals repr without full literal_eval."""
    blob = blob.strip()
    # Tuple / list value: 'bbox': (0.98, 0.95)
    m = re.search(r"""['"]bbox['"]\s*:\s*(\([^)]*\))""", blob)
    if m:
        return _parse_bbox_local(_strip_np_float64(m.group(1)))
    # String value from trace_plugin _safe_repr: 'bbox': '(0.98, 0.95)'
    m = re.search(r"""['"]bbox['"]\s*:\s*'(\([^)]*\))'""", blob)
    if m:
        return _parse_bbox_local(m.group(1))
    m = re.search(r'["\']bbox["\']\s*:\s*"(\([^)]*\))"', blob)
    if m:
        return _parse_bbox_local(m.group(1))
    return None


def _strip_np_float64(s: str) -> str:
    return re.sub(
        r"np\.float64\(\s*([^)]+?)\s*\)",
        r"\1",
        s,
        flags=re.IGNORECASE,
    )


def _to_jsonable(value):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return round(value, 15)
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    return str(value)


def _parse_bbox_local(raw) -> tuple[float, float, float, float]:
    """Reproduce Legend.set_bbox_to_anchor length-2 expansion before Bbox.from_bounds."""
    if isinstance(raw, (list, tuple)):
        bbox = raw
    else:
        s = _strip_np_float64(str(raw).strip())
        try:
            bbox = ast.literal_eval(s)
        except (SyntaxError, ValueError) as err:
            raise ValueError(f"Could not parse bbox local: {raw!r}") from err
    if isinstance(bbox, (list, tuple)):
        if len(bbox) == 2:
            return (float(bbox[0]), float(bbox[1]), 0.0, 0.0)
        if len(bbox) == 4:
            return tuple(float(x) for x in bbox)  # type: ignore[return-value]
    raise ValueError(f"Unexpected bbox shape after parse: {bbox!r}")


def extract_output(trace_text: str) -> dict[str, float]:
    matches: list[dict[str, str]] = []
    for raw in trace_text.splitlines():
        if "event=call" not in raw:
            continue
        if "set_bbox_to_anchor" not in raw:
            continue
        parsed = _parse_call_trace_line(raw)
        if not parsed:
            continue
        func = parsed["func"]
        if not func.endswith("set_bbox_to_anchor"):
            continue
        loc = _locals_dict_from_trace(parsed["locals"])
        bounds = None
        if loc is not None and "bbox" in loc:
            try:
                bounds = _parse_bbox_local(loc["bbox"])
            except ValueError:
                bounds = None
        if bounds is None:
            bounds = _bbox_from_locals_blob(parsed["locals"])
        if bounds is None:
            continue
        parsed["_bounds"] = bounds  # type: ignore[index]
        matches.append(parsed)

    if not matches:
        raise ValueError(
            "Could not find set_bbox_to_anchor call events in legend.py trace with a "
            "parsable bbox local. Ensure TRACE_FILE matches matplotlib/legend, "
            "TRACE_EVENTS includes call, and the trace log is non-empty."
        )

    def _is_test_anchor(b: tuple[float, float, float, float]) -> bool:
        left, bottom, width, height = b
        return (
            width == 0.0
            and height == 0.0
            and abs(left - 0.98) < 1e-9
            and abs(bottom - 0.95) < 1e-9
        )

    chosen = next((m for m in matches if _is_test_anchor(m["_bounds"])), matches[0])  # type: ignore[index]
    left, bottom, width, height = chosen["_bounds"]  # type: ignore[index]
    return {
        "left": _to_jsonable(left),
        "bottom": _to_jsonable(bottom),
        "width": _to_jsonable(width),
        "height": _to_jsonable(height),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/legend_bbox_anchor_offset_state_deep/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/legend_bbox_anchor_offset_state_deep/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    bounds = extract_output(trace_text)

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `tests/qa/legend_bbox_anchor_offset_state_deep_test.py`, class "
            "`TestLegendBboxAnchorOffsetStateDeepQA`, method "
            "`test_legend_bbox_anchor_offset_state_deep_case`. "
            "That test builds a multi-line legend with `bbox_to_anchor=(0.98, 0.95)` (see the "
            "`ax.legend(...)` call). During legend construction, Matplotlib calls "
            "`matplotlib.legend.Legend.set_bbox_to_anchor` with that 2-tuple. Inside that method, "
            "a 2-element bbox is expanded to four bounds before `Bbox.from_bounds` is applied. "
            "What are the four numeric values `(left, bottom, width, height)` passed to "
            "`Bbox.from_bounds` for that **first** `set_bbox_to_anchor` call in this test run?"
        ),
        "template_answer": {
            "left": "float",
            "bottom": "float",
            "width": "float",
            "height": "float",
        },
        "oracle_answer": bounds,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
