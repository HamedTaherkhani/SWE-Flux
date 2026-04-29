"""SFTTrainer construction with assistant-turn loss masking.

Loss is computed only on assistant (model) turns.  System prompts, user
messages, and tool-response messages are masked to -100 so they contribute
no gradient signal.  This is the correct objective for imitation-learning
from teacher trajectories.

Gemma 4 token boundaries
------------------------
  User turn     starts with:  <start_of_turn>user\n
  Model turn    starts with:  <start_of_turn>model\n
  Either turn   ends with:    <end_of_turn>\n

The local collator scans each tokenized conversation for model turns and masks
everything outside those spans to -100.  This replaces TRL's removed
DataCollatorForCompletionOnlyLM while keeping the same completion-only
training objective for preformatted chat transcripts.
"""

from __future__ import annotations

import logging
import inspect
from typing import Any, List

from datasets import Dataset
import torch
from trl import SFTConfig, SFTTrainer

from .config import TrainingConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chat-template boundary tokens for Gemma 4.
# If you change the base model family, update these to match its template.
# ---------------------------------------------------------------------------
RESPONSE_TEMPLATE = "<start_of_turn>model\n"
INSTRUCTION_TEMPLATE = "<start_of_turn>user\n"
END_TEMPLATE = "<end_of_turn>\n"


# ---------------------------------------------------------------------------
# Collator
# ---------------------------------------------------------------------------

class AssistantTurnDataCollator:
    """Pad tokenized examples and compute loss only on model turns."""

    def __init__(
        self,
        *,
        tokenizer: Any,
        response_template: List[int],
        end_template: List[int],
        max_length: int,
    ) -> None:
        self.tokenizer = tokenizer
        self.response_template = response_template
        self.end_template = end_template
        self.max_length = max_length
        self.pad_token_id = (
            tokenizer.pad_token_id
            if tokenizer.pad_token_id is not None
            else tokenizer.eos_token_id
        )
        self._warned_no_response = False

    @staticmethod
    def _find_subsequence(sequence: List[int], subsequence: List[int], start: int = 0) -> int:
        if not subsequence:
            return -1
        last_start = len(sequence) - len(subsequence)
        for idx in range(start, last_start + 1):
            if sequence[idx: idx + len(subsequence)] == subsequence:
                return idx
        return -1

    def _assistant_labels(self, input_ids: List[int]) -> List[int]:
        labels = [-100] * len(input_ids)
        cursor = 0
        found_response = False

        while cursor < len(input_ids):
            response_start = self._find_subsequence(
                input_ids,
                self.response_template,
                cursor,
            )
            if response_start == -1:
                break

            found_response = True
            label_start = response_start + len(self.response_template)
            end_start = self._find_subsequence(input_ids, self.end_template, label_start)
            label_end = len(input_ids) if end_start == -1 else end_start + len(self.end_template)

            labels[label_start:label_end] = input_ids[label_start:label_end]
            cursor = label_end

        if not found_response and not self._warned_no_response:
            logger.warning(
                "No assistant response boundary found in at least one batch item; "
                "that item will contribute no loss."
            )
            self._warned_no_response = True

        return labels

    def __call__(self, examples: List[dict[str, Any]]) -> dict[str, torch.Tensor]:
        input_id_lists: List[List[int]] = []
        label_lists: List[List[int]] = []

        for example in examples:
            input_ids = list(example["input_ids"])
            if self.max_length is not None:
                input_ids = input_ids[: self.max_length]

            input_id_lists.append(input_ids)
            label_lists.append(self._assistant_labels(input_ids))

        batch_size = len(input_id_lists)
        batch_max = max(len(ids) for ids in input_id_lists)

        input_ids_tensor = torch.full(
            (batch_size, batch_max),
            self.pad_token_id,
            dtype=torch.long,
        )
        attention_mask = torch.zeros((batch_size, batch_max), dtype=torch.long)
        labels_tensor = torch.full((batch_size, batch_max), -100, dtype=torch.long)

        for row, (input_ids, labels) in enumerate(zip(input_id_lists, label_lists)):
            length = len(input_ids)
            input_ids_tensor[row, :length] = torch.tensor(input_ids, dtype=torch.long)
            attention_mask[row, :length] = 1
            labels_tensor[row, :length] = torch.tensor(labels, dtype=torch.long)

        return {
            "input_ids": input_ids_tensor,
            "attention_mask": attention_mask,
            "labels": labels_tensor,
        }


def _build_collator(tokenizer: Any, max_length: int) -> AssistantTurnDataCollator:
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
    end_ids: List[int] = tokenizer.encode(
        END_TEMPLATE, add_special_tokens=False
    )

    collator = AssistantTurnDataCollator(
        tokenizer=tokenizer,
        response_template=response_ids,
        end_template=end_ids,
        max_length=max_length,
    )
    logger.info(
        "AssistantTurnDataCollator — response_ids: %s  instruction_ids: %s  end_ids: %s",
        response_ids, instruction_ids, end_ids,
    )
    return collator


# ---------------------------------------------------------------------------
# Training arguments
# ---------------------------------------------------------------------------

def _build_sft_config(cfg: TrainingConfig) -> SFTConfig:
    kwargs = dict(
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
        packing=False,   # packing would interleave conversations — keep them separate
    )
    sft_params = inspect.signature(SFTConfig.__init__).parameters
    length_param = (
        "max_seq_length"
        if "max_seq_length" in sft_params
        else "max_length"
    )
    kwargs[length_param] = cfg.data.max_seq_length

    unsupported = sorted(set(kwargs) - set(sft_params))
    for key in unsupported:
        kwargs.pop(key)
    if unsupported:
        logger.info("Ignoring unsupported SFTConfig arguments for this TRL version: %s", unsupported)

    return SFTConfig(**kwargs)


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
    collator = _build_collator(tokenizer, cfg.data.max_seq_length)
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
