"""Quantized model loading and LoRA adapter setup for QLoRA fine-tuning."""

from __future__ import annotations

import logging
from typing import Any, Tuple

import torch
from peft import LoraConfig as PeftLoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from .config import LoraConfig, QuantizationConfig

logger = logging.getLogger(__name__)

_DTYPE_MAP: dict[str, torch.dtype] = {
    "bfloat16": torch.bfloat16,
    "float16":  torch.float16,
    "float32":  torch.float32,
}


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def load_tokenizer(model_path: str) -> AutoTokenizer:
    """Load tokenizer with right-padding enabled (required for causal LM training)."""
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

    # Gemma and many other models set pad_token = eos_token by default.
    # Ensure it's set so DataCollator can pad batches.
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    # Right-padding keeps the causal attention mask aligned with labels.
    tokenizer.padding_side = "right"
    return tokenizer


# ---------------------------------------------------------------------------
# Quantization config
# ---------------------------------------------------------------------------

def _build_bnb_config(quant: QuantizationConfig) -> BitsAndBytesConfig:
    """
    Build a BitsAndBytesConfig for NF4 QLoRA.

    double_quant (nested quantization) reduces memory usage by ~0.4 bits/param
    at the cost of a small increase in quantization error — a good trade-off
    for fine-tuning tasks.
    """
    return BitsAndBytesConfig(
        load_in_4bit=quant.load_in_4bit,
        bnb_4bit_quant_type=quant.quant_type,
        bnb_4bit_compute_dtype=_DTYPE_MAP[quant.compute_dtype],
        bnb_4bit_use_double_quant=quant.double_quant,
    )


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

# flash_attn GPU kernels reject head_dim > 256 (see flash_attn_interface fwd).
_FLASH_ATTN_MAX_HEAD_DIM: int = 256


def _try_flash_attention() -> bool:
    try:
        import flash_attn  # noqa: F401
        return True
    except ImportError:
        return False


def _decoder_head_dim_from_config(config: Any) -> int | None:
    """Resolve self-attention head_dim for common HF layouts (incl. nested text_config)."""
    sub = getattr(config, "text_config", None)
    if sub is not None:
        config = sub
    head_dim = getattr(config, "head_dim", None)
    if head_dim is not None:
        return int(head_dim)
    hidden = getattr(config, "hidden_size", None)
    num_heads = getattr(config, "num_attention_heads", None)
    if hidden is not None and num_heads is not None and int(num_heads) > 0:
        return int(hidden) // int(num_heads)
    return None


def _flash_attention_compatible(model_path: str) -> bool:
    """True only if flash-attn is installed and model head_dim is within kernel limits."""
    if not _try_flash_attention():
        return False
    try:
        cfg = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
    except Exception as exc:  # pragma: no cover - network / path issues
        logger.warning("Could not load AutoConfig for FA2 check (%s); using sdpa.", exc)
        return False
    head_dim = _decoder_head_dim_from_config(cfg)
    if head_dim is None:
        logger.warning(
            "Could not infer attention head_dim for FA2 check; using sdpa to avoid FA2 runtime errors."
        )
        return False
    if head_dim > _FLASH_ATTN_MAX_HEAD_DIM:
        logger.info(
            "Flash Attention 2 not used — head_dim=%d exceeds flash-attn limit (%d); using sdpa",
            head_dim,
            _FLASH_ATTN_MAX_HEAD_DIM,
        )
        return False
    return True


def load_base_model(
    model_path: str,
    quant: QuantizationConfig,
) -> Any:
    """
    Load the base causal LM with optional 4-bit quantization.

    Uses Flash Attention 2 when installed and the model's head_dim is within
    flash-attn limits (≤256); otherwise uses SDPA.
    """
    compute_dtype = _DTYPE_MAP[quant.compute_dtype]

    model_kwargs: dict[str, Any] = {
        "trust_remote_code": True,
        "device_map": "auto",
        "torch_dtype": compute_dtype,
    }

    if quant.load_in_4bit:
        model_kwargs["quantization_config"] = _build_bnb_config(quant)

    if _flash_attention_compatible(model_path):
        model_kwargs["attn_implementation"] = "flash_attention_2"
        logger.info("Using Flash Attention 2")
    else:
        model_kwargs["attn_implementation"] = "sdpa"
        if _try_flash_attention():
            logger.info("Using sdpa attention (flash-attn installed but not used for this model)")
        else:
            logger.info("Flash Attention 2 not available — using sdpa attention")

    logger.info("Loading base model from %s ...", model_path)
    model = AutoModelForCausalLM.from_pretrained(model_path, **model_kwargs)

    if quant.load_in_4bit:
        # Wraps the model so that bitsandbytes 4-bit layers work correctly
        # with gradient checkpointing (which is crucial for memory efficiency).
        model = prepare_model_for_kbit_training(
            model,
            use_gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
        )

    return model


# ---------------------------------------------------------------------------
# LoRA setup
# ---------------------------------------------------------------------------

def _build_peft_config(lora: LoraConfig) -> PeftLoraConfig:
    """
    Build the PEFT LoraConfig.

    Targeting all linear projection matrices (q/k/v/o + gate/up/down) gives
    the best parameter efficiency vs. quality trade-off for instruction
    following and tool-use tasks.
    """
    return PeftLoraConfig(
        r=lora.r,
        lora_alpha=lora.alpha,
        lora_dropout=lora.dropout,
        target_modules=lora.target_modules,
        bias=lora.bias,
        task_type="CAUSAL_LM",
    )


def apply_lora(model: Any, lora: LoraConfig) -> Any:
    """Wrap the model with LoRA adapters and print trainable parameter count."""
    peft_config = _build_peft_config(lora)
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    return model


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_model_and_tokenizer(
    model_path: str,
    lora: LoraConfig,
    quant: QuantizationConfig,
) -> Tuple[Any, AutoTokenizer]:
    """
    Full setup: load quantized base model, apply LoRA, load tokenizer.

    Returns (peft_model, tokenizer).
    """
    tokenizer = load_tokenizer(model_path)
    model = load_base_model(model_path, quant)
    model = apply_lora(model, lora)
    return model, tokenizer
