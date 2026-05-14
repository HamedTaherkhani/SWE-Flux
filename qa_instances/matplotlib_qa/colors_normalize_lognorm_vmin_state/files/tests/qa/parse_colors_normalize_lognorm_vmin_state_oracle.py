#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


def _parse_return_trace_line(line: str) -> dict[str, str] | None:
    """Parse one trace_plugin return line (optional timestamp prefix)."""
    line = line.strip()
    if "event=return" not in line:
        return None
    m_ts = re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+\s+", line)
    if m_ts:
        line = line[m_ts.end() :]
    marker = " event=return retval="
    mi = line.find(marker)
    if mi < 0:
        return None
    head, rest = line[:mi], line[mi + len(marker) :]
    li = rest.rfind(" locals=")
    if li < 0:
        return None
    locals_raw = rest[li + len(" locals=") :]
    head_parts = head.rsplit(" ", 1)
    if len(head_parts) != 2:
        return None
    path_lineno, func = head_parts
    path, _, lineno = path_lineno.rpartition(":")
    if not path or not lineno.isdigit():
        return None
    return {
        "path": path,
        "lineno": lineno,
        "func": func,
        "retval": rest[:li].strip(),
        "locals": locals_raw,
    }


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


def parse_array_repr(arr_str: str):
    import numpy as np

    arr_str = str(arr_str).strip()
    if arr_str.startswith("array"):
        arr_str = arr_str[arr_str.index("(") + 1 : arr_str.rindex(")")]
    arr_str = re.sub(r"\s+", " ", arr_str)
    arr_str = arr_str.replace("[ ", "[").replace(" ]", "]")
    try:
        parsed = eval(arr_str)
        return np.asarray(parsed, dtype=float)
    except Exception:
        return None


def _coerce_vm(s: str):
    """Coerce traced vmin/vmax string repr to float or None."""
    s = str(s).strip()
    if s in ("None", "null"):
        return None
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        pass
    import numpy as np

    try:
        return float(eval(s, {"np": np, "numpy": np}))
    except Exception:
        return _to_jsonable(s)


def _vmin_vmax_from_locals(loc: dict) -> tuple[float | None, float | None] | None:
    """Derive vmin/vmax from traced locals at return of autoscale_None.

    In current Matplotlib, ``Normalize.autoscale_None`` sets ``self.vmin`` / ``self.vmax``
    and typically does **not** bind local names ``vmin`` / ``vmax``. The array passed in
    is available as local ``A`` (or ``in_trf_domain`` from ``LogNorm.autoscale_None``),
    and for unset limits the assigned limits equal that array's min and max.
    """
    if "vmin" in loc and "vmax" in loc:
        return _coerce_vm(loc["vmin"]), _coerce_vm(loc["vmax"])

    import numpy as np

    for key in ("A", "in_trf_domain"):
        if key not in loc:
            continue
        arr = parse_array_repr(str(loc[key]))
        if arr is None or arr.size == 0:
            continue
        try:
            flat = np.asarray(arr, dtype=float).ravel()
            flat = flat[np.isfinite(flat)]
            if flat.size == 0:
                continue
            return float(np.min(flat)), float(np.max(flat))
        except Exception:
            continue
    return None


def extract_output(trace_text: str) -> dict:
    matches: list[dict[str, str]] = []
    for raw in trace_text.splitlines():
        if "autoscale_None" not in raw or "event=return" not in raw:
            continue
        parsed = _parse_return_trace_line(raw)
        if not parsed:
            continue
        norm_path = parsed["path"].replace("\\", "/").lower()
        if "colors" not in norm_path:
            continue
        try:
            loc = ast.literal_eval(parsed["locals"])
        except (SyntaxError, ValueError):
            continue
        if _vmin_vmax_from_locals(loc) is None:
            continue
        matches.append(parsed)

    if not matches:
        raise ValueError(
            "Could not find autoscale_None return events in colors.py trace with "
            "vmin/vmax locals or array local A / in_trf_domain. "
            "Ensure TRACE_FILE matches matplotlib colors and return events are traced."
        )

    target = matches[-1]
    parsed_locals = ast.literal_eval(target["locals"])
    pair = _vmin_vmax_from_locals(parsed_locals)
    if pair is None:
        raise ValueError("Could not derive vmin/vmax from final autoscale_None locals.")
    vmin, vmax = pair

    return {
        "vmin": _to_jsonable(vmin),
        "vmax": _to_jsonable(vmax),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/colors_normalize_lognorm_vmin_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/colors_normalize_lognorm_vmin_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "C4_ProgramState",
        "question": (
            "Use `tests/qa/colors_normalize_lognorm_vmin_state_test.py`, class "
            "`TestColorsNormalizeLogNormVminStateQA`, method "
            "`test_colors_normalize_lognorm_vmin_state_case`. "
            "In that test, lines 10-15 define a 4x4 numpy array `data` with values ranging from 0.001 to 8.0, "
            "line 17 creates `norm = LogNorm()`, and line 19 calls `norm.autoscale(data)`. "
            "During this indirect execution, control reaches `matplotlib/colors.py::Normalize.autoscale_None` "
            "(possibly via a `LogNorm` override that forwards to the base implementation). "
            "That implementation sets ``self.vmin`` and ``self.vmax`` from the processed data when they were unset. "
            "What exact numeric values are ``self.vmin`` and ``self.vmax`` after this ``autoscale_None`` run completes "
            "(equivalently: the min and max of the array used to set those attributes when both were previously unset)?"
        ),
        "template_answer": {
            "vmin": "float | null",
            "vmax": "float | null",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
