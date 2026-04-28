"""Merge a QLoRA adapter into the base model weights for vLLM inference.

vLLM loads a plain HuggingFace model directory.  QLoRA adapters are separate
files (adapter_config.json + adapter_model.safetensors) that PEFT understands
but vLLM does not natively fuse at load time.  This module merges the low-rank
ΔW matrices back into the base weights (W ← W + BA) and saves a standard
model directory that vLLM can serve directly.

The merge is done in the dtype you specify (bfloat16 recommended) to avoid
precision loss.  No GPU is required — the operation runs on CPU if CUDA is
unavailable, though it is faster with a GPU.
"""

from __future__ import annotations

import logging
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from .config import MergeConfig

logger = logging.getLogger(__name__)

_DTYPE_MAP: dict[str, torch.dtype] = {
    "bfloat16": torch.bfloat16,
    "float16":  torch.float16,
}


def merge_adapter(
    adapter_path: Path,
    base_model: str,
    output_dir: Path,
    dtype: str = "bfloat16",
) -> None:
    """
    Load base model + LoRA adapter, merge weights, save for vLLM.

    Steps
    ─────
    1. Load base model in target dtype (no quantization — we need exact weights).
    2. Wrap with PeftModel using the saved adapter.
    3. Call merge_and_unload() — fuses ΔW into W and strips PEFT wrappers.
    4. Save model + tokenizer with safetensors serialization.

    Args:
        adapter_path: Directory produced by train.py (contains adapter_config.json).
        base_model:   Original HF model path or ID used during training.
        output_dir:   Destination for the merged model (can be loaded by vLLM).
        dtype:        Weight dtype of the merged model.  bfloat16 is recommended
                      for A100/H100; use float16 for older GPUs.
    """
    torch_dtype = _DTYPE_MAP.get(dtype, torch.bfloat16)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load base in full precision (not quantized — we need exact float weights
    # for the merge arithmetic to be correct).
    logger.info("Loading base model from %s in %s ...", base_model, dtype)
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch_dtype,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )

    logger.info("Applying adapter from %s ...", adapter_path)
    model = PeftModel.from_pretrained(base, str(adapter_path))

    logger.info("Merging LoRA weights into base model ...")
    model = model.merge_and_unload()
    model.eval()

    logger.info("Saving merged model to %s ...", output_dir)
    model.save_pretrained(
        str(output_dir),
        safe_serialization=True,     # safetensors — required for vLLM
        max_shard_size="4GB",
    )

    # The adapter directory also contains the tokenizer (we saved it there
    # during training).  Fall back to the base model tokenizer if not present.
    tokenizer_source = str(adapter_path) if (adapter_path / "tokenizer_config.json").exists() else base_model
    logger.info("Saving tokenizer from %s ...", tokenizer_source)
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source, trust_remote_code=True)
    tokenizer.save_pretrained(str(output_dir))

    logger.info("Merge complete.  Merged model: %s", output_dir)
    logger.info(
        "To serve with vLLM:\n"
        "  VLLM_MODEL=%s VLLM_TOOL_CALL_PARSER=gemma4 "
        "./evaluation_scripts/llm_eval/start_vllm.sh start",
        output_dir,
    )


def run_merge(cfg: MergeConfig) -> None:
    """Entry point called by the top-level merge.py CLI."""
    merge_adapter(
        adapter_path=cfg.adapter_path,
        base_model=cfg.base_model,
        output_dir=cfg.output_dir,
        dtype=cfg.dtype,
    )
