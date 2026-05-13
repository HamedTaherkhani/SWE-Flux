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
# Gemma 4 tool-call wire format
# ---------------------------------------------------------------------------
# vLLM's gemma4 tool parser expects assistant tool calls in this exact shape:
#
#   <|tool_call>call:NAME{key:<|"|>value<|"|>,num:42,flag:true}<tool_call|>
#
# i.e. bare keys (no quotes), string values delimited by <|"|>, bare numbers.
# Gemma 4's chat template fails to translate OpenAI-style `tool_calls` with a
# JSON-encoded `arguments` string into this format; the result is JSON-with-
# delimiters syntax that the parser then mangles into garbage dict keys
# (e.g. {'"path"': '"files/x.py"'}). The base model emits the right format
# because it was pretrained on it; fine-tuning on the wrong-format text teaches
# the student to emit broken calls.
#
# We sidestep the chat template's tool_call rendering: convert each assistant
# message's tool_calls into a content string already in wire format, then drop
# the tool_calls field so the template just passes the content through.

_GEMMA4_STR_DELIM = '<|"|>'
_GEMMA4_TOOL_START = "<|tool_call>"
_GEMMA4_TOOL_END = "<tool_call|>"


def _gemma4_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return f"{_GEMMA4_STR_DELIM}{v}{_GEMMA4_STR_DELIM}"
    if isinstance(v, list):
        return "[" + ",".join(_gemma4_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join(f"{k}:{_gemma4_value(x)}" for k, x in v.items()) + "}"
    return f"{_GEMMA4_STR_DELIM}{v}{_GEMMA4_STR_DELIM}"


def _gemma4_tool_call_text(name: str, arguments: Any) -> str:
    if isinstance(arguments, str):
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            args = {}
    else:
        args = arguments or {}
    body = ",".join(f"{k}:{_gemma4_value(v)}" for k, v in args.items())
    return f"{_GEMMA4_TOOL_START}call:{name}{{{body}}}{_GEMMA4_TOOL_END}"


def _rewrite_assistant_tool_calls(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Inline tool_calls into content using Gemma 4's wire format."""
    out: List[Dict[str, Any]] = []
    for m in messages:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            wire = "".join(
                _gemma4_tool_call_text(
                    tc.get("function", {}).get("name", ""),
                    tc.get("function", {}).get("arguments", "{}"),
                )
                for tc in m["tool_calls"]
            )
            content = (m.get("content") or "")
            new_content = (content + ("\n" if content.strip() else "") + wire).strip()
            out.append({"role": "assistant", "content": new_content})
        else:
            out.append(m)
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
            _rewrite_assistant_tool_calls(messages),
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
