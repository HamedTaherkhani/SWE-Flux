"""Dataset loading, repo filtering, and chat-template formatting for SFT.

Each training example is a complete multi-turn tool-use conversation stored as
an OpenAI-format messages list.  We format it using the model's own chat
template so the training distribution exactly matches what vLLM produces at
inference time with --tool-call-parser gemma4.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from datasets import Dataset

from .config import DataConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemma 4 tool-call normalization
# ---------------------------------------------------------------------------
# Current Gemma 4 chat templates natively render OpenAI-style `tool_calls` and
# following role="tool" messages into the wire format vLLM's gemma4 parser
# expects:
#   <|tool_call>call:NAME{key:<|"|>value<|"|>}<tool_call|>
#   <|tool_response>response:NAME{value:<|"|>{...}<|"|>}<tool_response|>
#
# Older SFT records in this repo baked the wire text directly into assistant
# content and often included prose before it. Normalize those records back into
# structured tool_calls, dropping the prose so the model is trained on the same
# protocol vLLM serves at evaluation time.

_GEMMA4_STR_DELIM = '<|"|>'
_GEMMA4_TOOL_START = "<|tool_call>"
_GEMMA4_TOOL_END = "<tool_call|>"


def _split_top_level(body: str) -> List[str]:
    parts: List[str] = []
    start = 0
    depth = 0
    in_gemma_string = False
    i = 0
    while i < len(body):
        if body.startswith(_GEMMA4_STR_DELIM, i):
            in_gemma_string = not in_gemma_string
            i += len(_GEMMA4_STR_DELIM)
            continue
        ch = body[i]
        if not in_gemma_string:
            if ch in "[{":
                depth += 1
            elif ch in "]}":
                depth = max(0, depth - 1)
            elif ch == "," and depth == 0:
                parts.append(body[start:i])
                start = i + 1
        i += 1
    tail = body[start:]
    if tail:
        parts.append(tail)
    return [p.strip() for p in parts if p.strip()]


def _parse_gemma4_value(raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith(_GEMMA4_STR_DELIM) and raw.endswith(_GEMMA4_STR_DELIM):
        return raw[len(_GEMMA4_STR_DELIM):-len(_GEMMA4_STR_DELIM)]
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw == "null":
        return None
    try:
        if any(ch in raw for ch in ".eE"):
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def _parse_gemma4_arguments(body: str) -> Dict[str, Any]:
    args: Dict[str, Any] = {}
    for part in _split_top_level(body):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        args[key.strip()] = _parse_gemma4_value(value)
    return args


def _arguments_to_mapping(arguments: Any) -> Any:
    if isinstance(arguments, dict):
        return arguments
    if not isinstance(arguments, str):
        return arguments or {}
    text = arguments.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return _parse_gemma4_arguments(text)


def _extract_inline_tool_calls(content: str) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []
    cursor = 0
    while True:
        start = content.find(_GEMMA4_TOOL_START, cursor)
        if start < 0:
            break
        end = content.find(_GEMMA4_TOOL_END, start)
        if end < 0:
            break
        inner = content[start + len(_GEMMA4_TOOL_START):end]
        cursor = end + len(_GEMMA4_TOOL_END)
        if not inner.startswith("call:") or "{" not in inner or not inner.endswith("}"):
            continue
        name_and_args = inner[len("call:"):]
        name, body = name_and_args.split("{", 1)
        calls.append(
            {
                "type": "function",
                "function": {
                    "name": name.strip(),
                    "arguments": _parse_gemma4_arguments(body[:-1]),
                },
            }
        )
    return calls


def normalize_messages_for_gemma4(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return messages in the native Gemma4/OpenAI tool-call shape.

    Tool-call assistant turns are content-free structured `tool_calls`; any
    natural-language preamble from older records is intentionally dropped.
    Role="tool" messages are preserved so the Gemma4 template renders native
    `<|tool_response>...<tool_response|>` blocks.
    """
    out: List[Dict[str, Any]] = []
    for idx, m in enumerate(messages):
        if m.get("role") != "assistant":
            out.append(dict(m))
            continue

        content = m.get("content") or ""
        tool_calls = m.get("tool_calls") or _extract_inline_tool_calls(content)
        if not tool_calls:
            out.append(dict(m))
            continue

        next_tool_ids = [
            follow.get("tool_call_id")
            for follow in messages[idx + 1:]
            if follow.get("role") == "tool"
        ]
        normalized_calls = []
        for call_idx, tc in enumerate(tool_calls):
            fn = dict(tc.get("function", {}))
            normalized = {
                "id": tc.get("id") or (next_tool_ids[call_idx] if call_idx < len(next_tool_ids) else f"call_{idx}_{call_idx}"),
                "type": tc.get("type", "function"),
                "function": {
                    "name": fn.get("name", ""),
                    "arguments": _arguments_to_mapping(fn.get("arguments", {})),
                },
            }
            normalized_calls.append(normalized)
        out.append({"role": "assistant", "content": "", "tool_calls": normalized_calls})
    return out

# ---------------------------------------------------------------------------
# Evaluation library bootstrap
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]  # fine-tuning/finetune/ -> RepoBehave/
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evaluation_scripts.llm_eval.repo_tools import TOOL_DESCRIPTIONS, TOOL_INPUT_SCHEMAS  # noqa: E402

# ---------------------------------------------------------------------------
# Tool definitions passed to apply_chat_template.
# These must match the tools provided to the vLLM server at inference time.
# ---------------------------------------------------------------------------
TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": TOOL_DESCRIPTIONS[name],
            "parameters": TOOL_INPUT_SCHEMAS[name],
        },
    }
    for name in ("list_dir", "read_file")
]

# Directories inside sft_dataset/ that are not repo data.
_NON_REPO_DIRS = {"repo_cache"}


# ---------------------------------------------------------------------------
# Record loading
# ---------------------------------------------------------------------------

def _discover_repos(dataset_dir: Path) -> List[str]:
    return sorted(
        d.name
        for d in dataset_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name not in _NON_REPO_DIRS
    )


def _load_records(dataset_dir: Path, repos: Optional[List[str]]) -> List[Dict[str, Any]]:
    """Load all per-instance JSON records, optionally filtered by repo list."""
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    available = _discover_repos(dataset_dir)
    target = repos if repos else available

    missing = [r for r in target if r not in available]
    if missing:
        raise ValueError(
            f"Requested repos not found in dataset: {missing}\n"
            f"Available: {available}"
        )

    records: List[Dict[str, Any]] = []
    for repo in target:
        repo_dir = dataset_dir / repo
        for jf in sorted(repo_dir.glob("*.json")):
            try:
                rec = json.loads(jf.read_text(encoding="utf-8"))
                if "messages" in rec and rec["messages"]:
                    records.append(rec)
                else:
                    logger.warning("Skipping %s — missing or empty messages", jf)
            except Exception as exc:
                logger.warning("Skipping %s: %s", jf, exc)

    logger.info("Loaded %d records from repos: %s", len(records), target)
    return records


# ---------------------------------------------------------------------------
# Chat-template formatting
# ---------------------------------------------------------------------------

def _format_messages(messages: List[Dict[str, Any]], tokenizer: Any) -> Optional[str]:
    """
    Apply the model's chat template to an OpenAI-format message list.

    Passing tools=TOOLS ensures the tool schemas are embedded in the formatted
    text exactly as vLLM embeds them when it receives an API request with those
    tools — keeping training and inference distributions identical.
    """
    try:
        text: str = tokenizer.apply_chat_template(
            normalize_messages_for_gemma4(messages),
            tools=TOOLS,
            tokenize=False,
            add_generation_prompt=False,
        )
        return text
    except Exception as exc:
        return None  # caller logs the failure


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_dataset(cfg: DataConfig, tokenizer: Any) -> Dataset:
    """
    Load SFT records, format each with the model's chat template, and return
    a HuggingFace Dataset with a single "text" column ready for SFTTrainer.
    """
    records = _load_records(cfg.dataset_dir, cfg.repos)

    texts: List[str] = []
    skipped = 0
    for rec in records:
        text = _format_messages(rec["messages"], tokenizer)
        if text is None:
            instance_id = rec.get("instance_id", "unknown")
            logger.warning(
                "Skipping %s/%s — apply_chat_template failed",
                rec.get("repo", "?"), instance_id,
            )
            skipped += 1
            continue
        texts.append(text)

    if skipped:
        logger.warning("%d records skipped due to formatting errors", skipped)

    logger.info("%d examples ready for training", len(texts))

    if not texts:
        raise RuntimeError(
            "No training examples could be formatted. "
            "Check that the tokenizer supports tool-call messages."
        )

    dataset = Dataset.from_dict({"text": texts})
    return dataset


def dataset_stats(dataset: Dataset, tokenizer: Any, max_seq_length: int) -> None:
    """Log length distribution and truncation warnings."""
    lengths = [len(tokenizer.encode(t, add_special_tokens=False)) for t in dataset["text"]]
    truncated = sum(1 for l in lengths if l > max_seq_length)
    logger.info(
        "Sequence lengths — min: %d  median: %d  max: %d  truncated (>%d): %d/%d",
        min(lengths),
        sorted(lengths)[len(lengths) // 2],
        max(lengths),
        max_seq_length,
        truncated,
        len(lengths),
    )
