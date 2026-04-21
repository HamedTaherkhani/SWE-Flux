#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def _load_route_cells(source_path: Path):
    spec = importlib.util.spec_from_file_location(
        "_grid_path_probe_mod",
        source_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {source_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    fn = getattr(mod, "route_cells", None)
    if fn is None:
        raise RuntimeError("route_cells not found in module.")
    return fn


def _line_sequence_for_call(route_cells, u: int, v: int) -> list[int]:
    seq: list[int] = []

    def tracer(frame, event, arg):  # type: ignore[no-untyped-def]
        if event != "line":
            return tracer
        if frame.f_code.co_name != "route_cells":
            return tracer
        seq.append(frame.f_lineno)
        return tracer

    sys.settrace(tracer)
    try:
        route_cells(u, v)
    finally:
        sys.settrace(None)
    return seq


def path_deterministic_five_calls(source_path: Path, u: int, v: int) -> bool:
    route_cells = _load_route_cells(source_path)
    sequences = [_line_sequence_for_call(route_cells, u, v) for _ in range(5)]
    first = sequences[0]
    return all(s == first for s in sequences[1:])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/voxel_route.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/grid_path_probe/oracle.json",
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.is_file():
        raise SystemExit(f"Missing source: {source_path}")

    det = path_deterministic_five_calls(source_path, 6, 9)

    qa = {
        "question_kind": "determinism_flakiness",
        "question": (
            "Use `test/qa/grid_path_probe_test.py`, class `TestGridPathProbeQA`, method "
            "`test_grid_path_probe_cases`, and execute the full parametrized suite in that file (all cases; "
            "more than fifteen rows). For the parametrized row with u=6 and v=9 (same as one case in that suite), "
            "run this experiment in one Python interpreter: import a fresh `yt_dlp/voxel_route.py` with no prior "
            "`route_cells` calls, then invoke `yt_dlp/voxel_route.py::route_cells` as `route_cells(6, 9)` exactly "
            "five times in immediate succession with no module reload and no other `route_cells` calls before or "
            "between those five. For each invocation, record the ordered list of source line numbers for every "
            "`line` trace event emitted while executing inside `route_cells` only, in execution order, producing "
            "five sequences S1 through S5. Return `path_deterministic` as a boolean: true if and only if "
            "S1, S2, S3, S4, and S5 are identical (same length and same line numbers in order), otherwise false."
        ),
        "template_answer": {
            "path_deterministic": "bool",
        },
        "oracle_answer": {
            "path_deterministic": det,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
