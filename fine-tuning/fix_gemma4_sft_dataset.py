#!/usr/bin/env python3
"""Normalize RepoBehave SFT records for Gemma4/vLLM tool calling.

Older records stored assistant turns as prose followed by literal Gemma4
`<|tool_call>...` text and converted tool results into user messages at load
time. For vLLM evaluation, Gemma4 should be trained on structured tool calls
and native role="tool" responses, letting the tokenizer chat template render:

  <|tool_call>call:...<tool_call|>
  <|tool_response>response:...<tool_response|>

Run with --write to update JSON records in place.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from finetune.data import TOOLS, normalize_messages_for_gemma4  # noqa: E402


_MODEL_TOOL_TURN_RE = re.compile(
    r"<\|turn>model\n(?P<body>.*?)(?=<\|turn>|$)",
    re.DOTALL,
)


def _record_paths(dataset_dir: Path) -> list[Path]:
    return sorted(
        p
        for p in dataset_dir.glob("*/*.json")
        if p.parent.name != "repo_cache"
    )


def _render(tokenizer: Any, messages: list[dict[str, Any]]) -> str:
    return tokenizer.apply_chat_template(
        messages,
        tools=TOOLS,
        tokenize=False,
        add_generation_prompt=False,
    )


def _render_errors(text: str) -> list[str]:
    errors: list[str] = []
    if "<tool_result" in text:
        errors.append("contains legacy <tool_result> user block")
    for match in _MODEL_TOOL_TURN_RE.finditer(text):
        body = match.group("body")
        if "<|tool_call>" not in body:
            continue
        prefix = body.split("<|tool_call>", 1)[0].strip()
        if prefix:
            errors.append("model tool-call turn has prose before <|tool_call>")
            break
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize Gemma4 SFT records and optionally validate rendered chat text.",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "sft_dataset",
    )
    parser.add_argument("--model", default="", help="Tokenizer/model path for render validation")
    parser.add_argument("--write", action="store_true", help="Rewrite JSON files in place")
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N files")
    args = parser.parse_args()

    paths = _record_paths(args.dataset_dir)
    if args.limit:
        paths = paths[: args.limit]

    tokenizer = None
    if args.model:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)

    changed = 0
    render_failures: list[str] = []
    legacy_inline_after = 0
    structured_calls_after = 0

    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        messages = record.get("messages") or []
        normalized = normalize_messages_for_gemma4(messages)

        if normalized != messages:
            changed += 1
            if args.write:
                record["messages"] = normalized
                path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        for message in normalized:
            if message.get("role") == "assistant" and "<|tool_call>" in (message.get("content") or ""):
                legacy_inline_after += 1
            if message.get("role") == "assistant" and message.get("tool_calls"):
                structured_calls_after += len(message["tool_calls"])

        if tokenizer is not None:
            try:
                text = _render(tokenizer, normalized)
            except Exception as exc:
                render_failures.append(f"{path}: render failed: {exc}")
                continue
            for error in _render_errors(text):
                render_failures.append(f"{path}: {error}")

    print(f"files checked: {len(paths)}")
    print(f"files changed: {changed}")
    print(f"structured tool calls after normalization: {structured_calls_after}")
    print(f"legacy inline tool-call assistant turns after normalization: {legacy_inline_after}")
    if render_failures:
        print("render validation failures:")
        for failure in render_failures[:20]:
            print(f"  - {failure}")
        if len(render_failures) > 20:
            print(f"  ... {len(render_failures) - 20} more")
        return 1
    if tokenizer is not None:
        print("render validation: ok")
    if changed and not args.write:
        print("dry run only; rerun with --write to update files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
