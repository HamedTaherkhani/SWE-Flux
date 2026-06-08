#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# The trace plugin emits per-line `event=line` entries whose `locals=...` block
# only contains the locals that *changed* since the previous event. We walk
# events in order, accumulate a cumulative snapshot, then pick the line-197
# event in the iteration where `i == 3` (the fourth and last iteration).
LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/yt_dlp/aes\.py):(?P<lineno>\d+) "
    r"(?P<func>yt_dlp\.aes\.aes_cbc_encrypt) "
    r"event=line locals=(?P<locals>\{.*\})$",
    re.MULTILINE,
)


TARGET_LINE = "197"
TARGET_I = 3


def extract_sizes(trace_text: str) -> dict:
    cumulative: dict[str, str] = {}
    target_snapshot: dict[str, str] | None = None

    for m in LINE_RE.finditer(trace_text):
        delta = ast.literal_eval(m.group("locals"))
        cumulative.update(delta)
        if m.group("lineno") == TARGET_LINE:
            i_text = cumulative.get("i")
            if i_text is None:
                continue
            i_val = ast.literal_eval(i_text)
            if i_val == TARGET_I:
                target_snapshot = dict(cumulative)
                break

    if target_snapshot is None:
        raise ValueError(
            f"Did not observe line {TARGET_LINE} with i == {TARGET_I} in trace.")

    def _len(name: str) -> int:
        if name not in target_snapshot:
            raise ValueError(f"`{name}` missing from snapshot")
        value = ast.literal_eval(target_snapshot[name])
        return len(value)

    return {
        "len_encrypted_data": _len("encrypted_data"),
        "len_encrypted_block": _len("encrypted_block"),
        "len_block": _len("block"),
        "len_mixed_block": _len("mixed_block"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/aes_cbc_encrypt_array_size/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/aes_cbc_encrypt_array_size/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    sizes = extract_sizes(trace_text)

    qa = {
        "question_kind": "S4_ProgramState",
        "question": (
            "Use `test/qa/aes_cbc_encrypt_array_size_test.py`, class "
            "`TestAesCbcEncryptArraySizeQA`, method "
            "`test_aes_cbc_encrypt_array_size_case`. "
            "The test calls "
            "`yt_dlp.aes.aes_cbc_encrypt(data=list(range(50)), key=list(range(16)), "
            "iv=list(range(16)), padding_mode='pkcs7')` "
            "(defined at line 175 in `yt_dlp/aes.py`). The function loops "
            "`for i in range(block_count):` at line 190 with `block_count = "
            "ceil(len(data) / BLOCK_SIZE_BYTES)` (`BLOCK_SIZE_BYTES = 16`). Each iteration "
            "executes line 191 (`block = data[i*16:(i+1)*16]`), line 192 "
            "(`block = pad_block(block, padding_mode)` -- pad_block is called on EVERY "
            "block, not only the last one, and PKCS#7 padding extends a sub-16-byte block "
            "up to 16 bytes while leaving an already-16-byte block unchanged), line 194 "
            "(`mixed_block = xor(block, previous_cipher_block)`), line 196 "
            "(`encrypted_block = aes_encrypt(mixed_block, expanded_key)`), and finally "
            "line 197 (`encrypted_data += encrypted_block`). "
            "Report the **lengths** of the four list locals at the trace event for line "
            "197 in the iteration where `i == 3` (the fourth and last iteration), at the "
            "moment the line-197 event fires -- i.e., AFTER lines 191/192/194/196 of "
            "iteration 3 have already executed but BEFORE the `+=` on line 197 has "
            "appended the new block to `encrypted_data`. "
            "Return a JSON object with four integer keys: `len_encrypted_data`, "
            "`len_encrypted_block`, `len_block`, `len_mixed_block`."
        ),
        "template_answer": {
            "len_encrypted_data": "int",
            "len_encrypted_block": "int",
            "len_block": "int",
            "len_mixed_block": "int",
        },
        "oracle_answer": sizes,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
