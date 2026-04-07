#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>\S+) event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


def _probe_line(source_text: str) -> int:
    tree = ast.parse(source_text)
    fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_infer_concat_order_from_coords":
            fn = node
            break
    if fn is None:
        raise ValueError("_infer_concat_order_from_coords not found.")

    for node in fn.body:
        if isinstance(node, ast.For):
            if_line = node.body[0].lineno if node.body else None
            if if_line is not None:
                return if_line
    raise ValueError("Could not locate loop probe line.")


def _tile_ids_len(value_repr: str) -> int:
    try:
        node = ast.parse(value_repr, mode="eval").body
    except SyntaxError as e:
        raise ValueError(f"tile_ids repr is not valid Python: {value_repr!r}") from e
    if not isinstance(node, ast.List):
        raise ValueError("tile_ids is not a list repr.")
    return len(node.elts)


def _datasets_count(value_repr: str) -> int:
    # datasets is traced as a repr string of a list of Dataset reprs.
    count = value_repr.count("<xarray.Dataset>")
    if count > 0:
        return count
    # fallback for uncommon repr variants
    return value_repr.count("Dataset>")


def extract_invariant(trace_text: str, source_text: str) -> dict[str, object]:
    _probe_line(source_text)  # structural check that target loop exists
    observed_lens: list[int] = []
    pair_observations: list[tuple[int, int]] = []
    current_dataset_count: int | None = None

    for m in LINE_RE.finditer(trace_text):
        func = m.group("func")
        if not func.endswith("._infer_concat_order_from_coords"):
            continue

        locals_map = ast.literal_eval(m.group("locals"))
        if "datasets" in locals_map:
            ds_count = _datasets_count(locals_map["datasets"])
            if ds_count > 0:
                current_dataset_count = ds_count

        if "tile_ids" in locals_map:
            tile_len = _tile_ids_len(locals_map["tile_ids"])
            observed_lens.append(tile_len)
            if current_dataset_count is not None:
                pair_observations.append((tile_len, current_dataset_count))

    if not observed_lens or not pair_observations:
        raise ValueError("No loop observations found for tile_ids length.")

    holds = all(tile_len == ds_count for tile_len, ds_count in pair_observations)
    return {
        "holds_across_all_loop_iterations": holds,
        "observed_tile_ids_lengths": sorted(set(observed_lens)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/combine_tile_ids_length_loop_invariant/trace.log",
    )
    parser.add_argument(
        "--source-file",
        default="/testbed/xarray/core/combine.py",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/combine_tile_ids_length_loop_invariant/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    source_text = Path(args.source_file).read_text(encoding="utf-8")
    output = extract_invariant(trace_text, source_text)

    qa = {
        "question_kind": "invariant_properties",
        "question": (
            "Use `xarray/tests/qa/combine_tile_ids_length_loop_invariant_test.py`, class "
            "`TestCombineTileIdsLengthLoopInvariantHardQA`, and execute the full suite in that file "
            "(both test methods). During this suite, inspect `_infer_concat_order_from_coords` in the "
            "combine module (`xarray/core/combine.py` or `xarray/structure/combine.py`, depending on "
            "version), specifically the loop `for dim in ds0.dims:`. In this question, an invariant means "
            "a condition that must remain true at every checked loop iteration during execution. Evaluate "
            "whether `len(tile_ids)` equals the number of input datasets at each checked iteration. Here, "
            "`observed_tile_ids_lengths` means the list of concrete `len(tile_ids)` values recorded at "
            "those loop-check points across the full executed suite. Return whether the condition holds "
            "across all checked iterations and the recorded `observed_tile_ids_lengths`."
        ),
        "template_answer": {
            "holds_across_all_loop_iterations": "bool",
            "observed_tile_ids_lengths": ["int"],
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
