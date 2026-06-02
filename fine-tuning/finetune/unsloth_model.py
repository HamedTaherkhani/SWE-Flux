"""Unsloth FastModel loading and LoRA setup — the long-context training path.

This is an alternative backend to model.py. It loads the base model and applies
LoRA through Unsloth's FastModel API instead of transformers + bitsandbytes +
PEFT. Unsloth's fused kernels and "unsloth" gradient checkpointing fit a much
larger context window on the same H100, which is the reason this path exists.

Everything downstream is unchanged: the tokenizer (and therefore the chat
template, tool-call wire format, and assistant-turn loss masking), the dataset,
the custom collator, and the TRL SFTTrainer are all shared with the default
path. Unsloth monkeypatches TRL/transformers so the same SFTTrainer just works.

`import unsloth` must run before transformers/trl are imported for the patches
to take effect — train.py handles that early import; this module imports
FastModel lazily inside the loader so importing the package never pulls in
Unsloth on the default path.

Focused on gemma4-4b today (multimodal: LoRA is scoped to the language tower
via finetune_vision_layers=False). Other models like Qwen work through the same
function with no special-casing — pass --model and --use-unsloth.
"""

from __future__ import annotations

import contextlib
import functools
import logging
from typing import Any, Iterator, List, Tuple

import torch

from .config import LoraConfig, QuantizationConfig
from .model import _DTYPE_MAP, load_tokenizer

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def _force_no_kv_sharing() -> Iterator[None]:
    """
    Force num_kv_shared_layers=0 on every config loaded inside this block.

    Unsloth's FastModel.from_pretrained doesn't accept a `config=` override, so
    we patch transformers.AutoConfig.from_pretrained for the duration of the
    load. This makes transformers materialize all 42 K/V projections (instead of
    sharing the top 18), matching the on-disk base checkpoint and vLLM's runtime
    view — without it the trained adapter is invalid under vLLM for gemma4-4b.
    See finetune/model.py:_override_kv_sharing for the full rationale.
    """
    import transformers

    orig = transformers.AutoConfig.from_pretrained

    @functools.wraps(orig)
    def patched(*args: Any, **kwargs: Any):
        cfg = orig(*args, **kwargs)
        text = getattr(cfg, "text_config", cfg)
        if getattr(text, "num_kv_shared_layers", 0):
            logger.info(
                "Unsloth: overriding num_kv_shared_layers %d -> 0 (vLLM/base match)",
                text.num_kv_shared_layers,
            )
            text.num_kv_shared_layers = 0
        return cfg

    transformers.AutoConfig.from_pretrained = patched
    try:
        yield
    finally:
        transformers.AutoConfig.from_pretrained = orig


def _unwrap_tokenizer(maybe_processor: Any, model_path: str) -> Any:
    """
    Return a real tokenizer from whatever FastModel handed back.

    For multimodal models (e.g. gemma4-4b) Unsloth returns a Processor
    (Gemma4Processor) whose text tokenizer lives at `.tokenizer`. The dataset
    and collator call `.encode` / `.apply_chat_template`, which a processor does
    not fully expose, so unwrap to the inner tokenizer to match the default path.
    """
    tok = maybe_processor
    if tok is None:
        return load_tokenizer(model_path)
    if not hasattr(tok, "encode") and hasattr(tok, "tokenizer"):
        logger.info("Unsloth returned a %s; using its inner .tokenizer", type(tok).__name__)
        tok = tok.tokenizer
    return tok

# Unsloth's get_peft_model wants a plain list of projection names. The default
# transformers path uses a regex for gemma4-4b to scope LoRA to the language
# model; under Unsloth that scoping is done with finetune_vision_layers=False
# instead, so we fall back to this explicit list when a regex is supplied.
_DEFAULT_TARGET_MODULES: List[str] = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]


def _resolve_target_modules(lora: LoraConfig) -> List[str]:
    """Unsloth needs a list; convert the gemma4 regex form to the default list."""
    if isinstance(lora.target_modules, str):
        logger.info(
            "Unsloth path: regex target_modules (%r) replaced with the default "
            "projection list; language-only scoping is handled by "
            "finetune_vision_layers=False.",
            lora.target_modules,
        )
        return list(_DEFAULT_TARGET_MODULES)
    return list(lora.target_modules)


def load_model_and_tokenizer_unsloth(
    model_path: str,
    lora: LoraConfig,
    quant: QuantizationConfig,
    max_seq_length: int,
) -> Tuple[Any, Any]:
    """
    Load the base model + LoRA via Unsloth FastModel.

    Returns (peft_model, tokenizer). Mirrors
    finetune.model.load_model_and_tokenizer so train.py can swap backends with a
    single branch.
    """
    from unsloth import FastModel  # lazy: only import on the unsloth path

    compute_dtype = _DTYPE_MAP[quant.compute_dtype]

    load_kwargs: dict[str, Any] = dict(
        model_name=model_path,
        max_seq_length=max_seq_length,
        dtype=compute_dtype,
        load_in_4bit=quant.load_in_4bit,
        full_finetuning=False,
        trust_remote_code=True,
    )

    logger.info(
        "Loading base model via Unsloth FastModel from %s (max_seq_length=%d, 4bit=%s) ...",
        model_path, max_seq_length, quant.load_in_4bit,
    )
    # The num_kv_shared_layers=0 override is applied by patching AutoConfig for
    # the duration of the load (FastModel rejects a `config=` kwarg).
    with _force_no_kv_sharing():
        model, processor = FastModel.from_pretrained(**load_kwargs)

    # Confirm the override actually took effect; warn loudly if KV-sharing is
    # still active, because the merged adapter would then be invalid under vLLM.
    _text_cfg = getattr(model.config, "text_config", model.config)
    _shared = getattr(_text_cfg, "num_kv_shared_layers", 0)
    if _shared:
        logger.warning(
            "num_kv_shared_layers is still %d after load — the KV-sharing "
            "override did NOT take effect. The merged adapter may be INVALID "
            "under vLLM for gemma4-4b; verify serving coherence.",
            _shared,
        )
    else:
        logger.info("Confirmed num_kv_shared_layers=0 after load (vLLM-compatible).")

    # Unsloth returns a Processor for multimodal models; unwrap to the text
    # tokenizer, then match the default path's pad/padding normalization so the
    # shared collator behaves identically.
    tokenizer = _unwrap_tokenizer(processor, model_path)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    tokenizer.padding_side = "right"

    target_modules = _resolve_target_modules(lora)
    logger.info(
        "Applying LoRA via Unsloth get_peft_model — r=%d alpha=%d dropout=%g targets=%s",
        lora.r, lora.alpha, lora.dropout, target_modules,
    )
    model = FastModel.get_peft_model(
        model,
        r=lora.r,
        lora_alpha=lora.alpha,
        lora_dropout=lora.dropout,
        target_modules=target_modules,
        bias=lora.bias,
        # gemma4-4b is multimodal — keep LoRA on the language tower only,
        # matching the regex scoping used by the default path.
        finetune_vision_layers=False,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
        # Unsloth's offloaded checkpointing is what unlocks the long context.
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )
    return model, tokenizer
