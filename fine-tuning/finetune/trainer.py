"""SFTTrainer construction with completion-only loss masking.

Loss is computed only on assistant (model) turns.  System prompts, user
messages, and tool-response messages are masked to -100 so they contribute
no gradient signal.  This is the correct objective for imitation-learning
from teacher trajectories.

Gemma 4 token boundaries
─────────────────────────
  User turn     starts with:  <start_of_turn>user\n
  Model turn    starts with:  <start_of_turn>model\n
  Either turn   ends with:    <end_of_turn>\n

DataCollatorForCompletionOnlyLM scans the tokenized sequence for every
occurrence of the response_template token ids and masks everything that
precedes each occurrence.  With a multi-turn conversation this correctly
unmasks all model turns in one pass.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from datasets import Dataset

try:
    from trl import SFTConfig, SFTTrainer, DataCollatorForCompletionOnlyLM
except ImportError:
    # Older TRL (< 0.10) used a different import path for the collator.
    from trl import SFTConfig, SFTTrainer
    from trl.trainer import DataCollatorForCompletionOnlyLM  # type: ignore[no-redef]

from .config import TrainingConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chat-template boundary tokens for Gemma 4.
# If you change the base model family, update these to match its template.
# ---------------------------------------------------------------------------
RESPONSE_TEMPLATE = "<start_of_turn>model\n"
INSTRUCTION_TEMPLATE = "<start_of_turn>user\n"


# ---------------------------------------------------------------------------
# Collator
# ---------------------------------------------------------------------------

def _build_collator(tokenizer: Any) -> DataCollatorForCompletionOnlyLM:
    """
    Build a completion-only data collator that masks non-assistant tokens.

    We tokenize the boundary strings without special tokens so we get the
    exact sub-sequence that appears inside a fully-formatted conversation,
    avoiding off-by-one BOS/EOS issues.
    """
    response_ids: List[int] = tokenizer.encode(
        RESPONSE_TEMPLATE, add_special_tokens=False
    )
    instruction_ids: List[int] = tokenizer.encode(
        INSTRUCTION_TEMPLATE, add_special_tokens=False
    )

    collator = DataCollatorForCompletionOnlyLM(
        response_template=response_ids,
        instruction_template=instruction_ids,
        tokenizer=tokenizer,
        mlm=False,
    )
    logger.info(
        "DataCollatorForCompletionOnlyLM — response_ids: %s  instruction_ids: %s",
        response_ids, instruction_ids,
    )
    return collator


# ---------------------------------------------------------------------------
# Training arguments
# ---------------------------------------------------------------------------

def _build_sft_config(cfg: TrainingConfig) -> SFTConfig:
    return SFTConfig(
        # Output
        output_dir=str(cfg.output_dir),

        # Epochs / steps
        num_train_epochs=cfg.num_epochs,

        # Batch size and gradient accumulation
        per_device_train_batch_size=cfg.per_device_batch_size,
        gradient_accumulation_steps=cfg.gradient_accumulation_steps,

        # Optimizer
        optim=cfg.optim,
        learning_rate=cfg.learning_rate,
        lr_scheduler_type=cfg.lr_scheduler,
        warmup_ratio=cfg.warmup_ratio,
        weight_decay=cfg.weight_decay,
        max_grad_norm=cfg.max_grad_norm,

        # Precision — bf16 + tf32 is the recommended QLoRA setup on A100/H100
        bf16=True,
        tf32=True,

        # Memory — gradient checkpointing is essential for long sequences
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},

        # Logging
        logging_strategy="steps",
        logging_steps=cfg.logging_steps,
        report_to=cfg.report_to,

        # Checkpointing
        save_strategy="steps",
        save_steps=cfg.save_steps,
        save_total_limit=cfg.save_total_limit,
        load_best_model_at_end=False,  # no eval set — just save latest

        # Data loading
        dataloader_num_workers=4,
        dataloader_pin_memory=True,

        # Group sequences of similar length together to minimize padding waste.
        group_by_length=True,

        # SFT-specific
        dataset_text_field="text",
        max_seq_length=cfg.data.max_seq_length,
        packing=False,   # packing would interleave conversations — keep them separate
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_trainer(
    cfg: TrainingConfig,
    model: Any,
    tokenizer: Any,
    dataset: Dataset,
) -> SFTTrainer:
    """Build the SFTTrainer.  Caller is responsible for calling .train()."""
    collator = _build_collator(tokenizer)
    sft_cfg = _build_sft_config(cfg)

    trainer = SFTTrainer(
        model=model,
        args=sft_cfg,
        train_dataset=dataset,
        data_collator=collator,
        processing_class=tokenizer,
    )

    total_steps = (
        len(dataset)
        // (cfg.per_device_batch_size * cfg.gradient_accumulation_steps)
        * cfg.num_epochs
    )
    logger.info(
        "Training plan: %d examples × %d epochs / (batch %d × accum %d) ≈ %d optimizer steps",
        len(dataset), cfg.num_epochs,
        cfg.per_device_batch_size, cfg.gradient_accumulation_steps,
        total_steps,
    )

    return trainer
