#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def _load_stride_snap(source_path: Path):
    spec = importlib.util.spec_from_file_location(
        "_stride_repeat_probe_mod",
        source_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {source_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    snap = getattr(mod, "stride_snap", None)
    if snap is None:
        raise RuntimeError("stride_snap not found in module.")
    return snap


def output_deterministic_for_five_calls(source_path: Path, a: int, b: int) -> bool:
    stride_snap = _load_stride_snap(source_path)
    outs = [stride_snap(a, b) for _ in range(5)]
    return len(set(outs)) == 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/raster_stride.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/stride_repeat_probe/oracle.json",
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.is_file():
        raise SystemExit(f"Missing source: {source_path}")

    det = output_deterministic_for_five_calls(source_path, 19, 5)

    qa = {
        "question_kind": "determinism_flakiness",
        "question": (
            "Use `test/qa/stride_repeat_probe_test.py`, class `TestStrideRepeatProbeQA`, method "
            "`test_stride_repeat_probe_cases`, and execute the full parametrized suite in that file (all cases; "
            "more than fifteen rows). For the parametrized row with a=19 and b=5, answer this output-determinism "
            "question: in one Python interpreter, import a fresh `yt_dlp/raster_stride.py` with no prior "
            "`stride_snap` calls, then invoke `yt_dlp/raster_stride.py::stride_snap` as `stride_snap(19, 5)` "
            "exactly five times in immediate succession with no module reload and no other `stride_snap` calls "
            "before or between those five. Are all five returned integers bitwise identical? Return "
            "`output_deterministic` as a boolean, true only if all five return values are equal."
        ),
        "template_answer": {
            "output_deterministic": "bool",
        },
        "oracle_answer": {
            "output_deterministic": det,
        },
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
