#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def _load_module(source_path: Path):
    spec = importlib.util.spec_from_file_location(
        "_shadow_blend_probe_mod",
        source_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {source_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def capture_inner_blend_entry(
    source_path: Path,
    k: int,
    tag: str,
) -> dict[str, object]:
    mod = _load_module(source_path)
    orig = mod.inner_blend
    box: dict[str, object] = {}

    def shim(acc, slot, flag):  # type: ignore[no-untyped-def]
        if not box:
            box["acc"] = int(acc)
            box["slot"] = int(slot)
            box["flag"] = bool(flag)
        return orig(acc, slot, flag)

    mod.inner_blend = shim  # type: ignore[assignment]
    mod.outer_wire(k, tag)
    if not box:
        raise RuntimeError("inner_blend was not reached.")
    return {
        "acc": box["acc"],
        "slot": box["slot"],
        "flag": box["flag"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default="/testbed/yt_dlp/hinge_cascade.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/shadow_blend_probe/oracle.json",
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.is_file():
        raise SystemExit(f"Missing source: {source_path}")

    answer = capture_inner_blend_entry(source_path, 5, "ab")

    qa = {
        "question_kind": "program_state_prediction",
        "question": (
            "Use `test/qa/shadow_blend_probe_test.py`, class `TestShadowBlendProbeQA`, method "
            "`test_shadow_blend_probe_case`. At line 8, the test calls `outer_wire(5, \"ab\")` from "
            "`yt_dlp/hinge_cascade.py`; that path reaches `yt_dlp/hinge_cascade.py::inner_blend` "
            "indirectly (the test never names `inner_blend`). At entry to the first `inner_blend` "
            "invocation on that path (parameter binding for the call, before any line of the callee "
            "body runs), what are the exact values of parameters `acc`, `slot`, and `flag`?"
        ),
        "template_answer": {
            "acc": "int",
            "slot": "int",
            "flag": "bool",
        },
        "oracle_answer": answer,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
