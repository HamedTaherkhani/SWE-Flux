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
    if "event=return" not in line or "polar" not in line.lower():
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

    # head: <path>:<lineno> <qualname> — split qualname from path:lineno at last space
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


def _is_forward_polar_theta_r_state(loc: dict) -> bool:
    """True for PolarTransform.transform_non_affine return locals, not InvertedPolarTransform.

    Forward path does ``theta, r = transpose(values)`` and does not bind ``x``/``y``.
    Inverse binds ``x, y = values.T`` so both ``x`` and ``y`` appear in locals at return.
    """
    if "theta" not in loc or "r" not in loc:
        return False
    if "x" in loc and "y" in loc:
        return False
    return True


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


def _x_y_from_retval(retval_s: str) -> tuple[str, str]:
    """Recover Cartesian x,y string reprs from logged return value (nx2 array)."""
    import numpy as np

    s = str(retval_s).strip()
    if "..." in s:
        s = s[: s.index("...")].rstrip()
    arr = parse_array_repr(s)
    if arr is None or arr.size < 2:
        raise ValueError("Could not parse retval as array with x,y.")
    flat = arr.reshape(-1)
    x_repr = str(np.array([[float(flat[0])]]))[:100]
    y_repr = str(np.array([[float(flat[1])]]))[:100]
    return x_repr, y_repr


def _x_y_from_theta_r(theta_s: str, r_s: str) -> tuple[str, str]:
    import numpy as np

    t = parse_array_repr(theta_s)
    r = parse_array_repr(r_s)
    if t is None or r is None:
        raise ValueError("Could not parse theta/r reprs.")
    x = r * np.cos(t)
    y = r * np.sin(t)
    x_repr = str(np.array([[float(np.reshape(x, (-1,))[0])]]))[:100]
    y_repr = str(np.array([[float(np.reshape(y, (-1,))[0])]]))[:100]
    return x_repr, y_repr


def extract_output(trace_text: str) -> dict:
    matches: list[dict[str, str]] = []
    for raw in trace_text.splitlines():
        if "transform_non_affine" not in raw or "event=return" not in raw:
            continue
        if "InvertedPolarTransform" in raw:
            continue
        parsed = _parse_return_trace_line(raw)
        if not parsed:
            continue
        norm_path = parsed["path"].replace("\\", "/")
        if "polar" not in norm_path.lower():
            continue
        try:
            loc = ast.literal_eval(parsed["locals"])
        except (SyntaxError, ValueError):
            continue
        if not _is_forward_polar_theta_r_state(loc):
            continue
        matches.append(parsed)

    if not matches:
        raise ValueError(
            "Could not find a forward polar transform_non_affine return in trace log "
            "(expected return from PolarTransform with theta/r locals, not InvertedPolarTransform). "
            "Ensure TRACE_FILE matches matplotlib polar projection source and TRACE_EVENTS includes return."
        )

    target = matches[-1]
    parsed_locals = ast.literal_eval(target["locals"])

    theta_val = parsed_locals["theta"]
    r_val = parsed_locals["r"]
    x_val = parsed_locals.get("x")
    y_val = parsed_locals.get("y")

    if x_val is None or y_val is None:
        try:
            x_val, y_val = _x_y_from_retval(target["retval"])
        except Exception:
            x_val, y_val = _x_y_from_theta_r(str(theta_val), str(r_val))

    return {
        "theta_repr": str(theta_val)[:100],
        "r_repr": str(r_val)[:100],
        "x_repr": str(x_val)[:100],
        "y_repr": str(y_val)[:100],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/axes_polar_transform_state_complex/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/axes_polar_transform_state_complex/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_output(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `tests/qa/axes_polar_transform_state_complex_test.py`, class "
            "`TestAxesPolarTransformStateComplexQA`, method "
            "`test_axes_polar_transform_state_complex_case`. "
            "In that test, lines 12-20 set up a polar plot with 12 bars using `ax.bar()`, "
            "lines 27-29 configure the polar axes with `set_theta_zero_location('N')` and `set_theta_direction(-1)`, "
            "line 31 obtains `transform_pipeline = ax.transData`, line 33 defines `test_point = np.array([[np.pi / 4, 5.0]])`, "
            "and line 34 calls `transformed = transform_pipeline.transform(test_point)`. "
            "During this indirect execution through the composite transform chain, control eventually reaches "
            "`matplotlib/projections/polar.py::PolarTransform.transform_non_affine`. "
            "Inside this function, after coordinate transformation logic processes the input, local variables `theta` and `r` "
            "are available (and the Cartesian coordinates may appear as separate locals or only in the returned array). "
            "At the return statement of `transform_non_affine`, what are the exact string "
            "representations (first 100 characters) of `theta`, `r`, and the Cartesian coordinates "
            "that correspond to `x` and `y` (use the return value's columns if `x`/`y` are not separate locals)?"
        ),
        "template_answer": {
            "theta_repr": "str",
            "r_repr": "str",
            "x_repr": "str",
            "y_repr": "str",
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
