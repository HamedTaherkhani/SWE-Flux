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
import os
from typing import Any, List

from datasets import Dataset
import torch
from trl import SFTConfig, SFTTrainer

from .config import TrainingConfig

logger = logging.getLogger(__name__)

# Chat-turn boundary token sequences are discovered at runtime by probing the
# tokenizer's chat template — see _discover_chat_boundaries below. This avoids
# the trap where a model's literal `<start_of_turn>` string tokenizes as
# unrelated BPE pieces while the template emits a single special token id.


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


def _discover_chat_boundaries(tokenizer: Any) -> tuple[List[int], List[int]]:
    """
    Probe the model's chat template to find the actual token sub-sequences that
    delimit an assistant turn.

    Why this can't be hardcoded: Gemma 4 (and many other models) uses
    chat-template special tokens that don't match their *literal string*
    representation. For example, `<start_of_turn>` may render as `<|turn>` in
    the template output and live as a single special token id (e.g. 105) — but
    `tokenizer.encode("<start_of_turn>", ...)` falls through to the BPE encoder
    and returns 9 unrelated tokens, none of which appear in actual training
    data. The collator then masks every label to -100, gradients vanish, and
    training silently no-ops.

    Strategy: build a minimal probe conversation with a unique marker as the
    assistant content, tokenize through the chat template, and extract the
    tokens immediately surrounding the marker. Those are the real boundaries.

    Returns (response_template, end_template) as token id lists.
    """
    marker = "RESPONSEBOUNDARYPROBE"
    text = tokenizer.apply_chat_template(
        [
            {"role": "user", "content": "u"},
            {"role": "assistant", "content": marker},
        ],
        tokenize=False,
        add_generation_prompt=False,
    )
    ids: List[int] = tokenizer.encode(text, add_special_tokens=False)
    marker_ids: List[int] = tokenizer.encode(marker, add_special_tokens=False)

    # Locate the marker in the templated tokens.
    marker_pos = -1
    for i in range(len(ids) - len(marker_ids) + 1):
        if ids[i : i + len(marker_ids)] == marker_ids:
            marker_pos = i
            break
    if marker_pos < 0:
        raise RuntimeError(
            "Could not locate probe marker in chat-template output; cannot "
            "discover assistant-turn boundaries automatically. Templated text: "
            f"{text!r}"
        )

    # The 3 tokens before the marker are the assistant-turn opening
    # (start_of_turn, "model", \n) for Gemma-style templates. We take 3 because
    # that's the structural width of the opening; if a template uses a
    # different width, this still yields a unique sub-sequence per turn.
    response_template = ids[max(0, marker_pos - 3) : marker_pos]

    # The 2 tokens after the marker are the turn-ending (end_of_turn, \n).
    marker_end = marker_pos + len(marker_ids)
    end_template = ids[marker_end : marker_end + 2]

    if not response_template or not end_template:
        raise RuntimeError(
            "Discovered empty chat-turn boundaries. Templated text: "
            f"{text!r}, ids: {ids}"
        )
    return response_template, end_template


def _build_collator(tokenizer: Any, max_length: int) -> AssistantTurnDataCollator:
    """
    Build a completion-only data collator that masks non-assistant tokens.

    Boundaries are discovered from the tokenizer's chat template at runtime
    (see _discover_chat_boundaries) so this works regardless of which special
    tokens the model uses.
    """
    response_ids, end_ids = _discover_chat_boundaries(tokenizer)

    collator = AssistantTurnDataCollator(
        tokenizer=tokenizer,
        response_template=response_ids,
        end_template=end_ids,
        max_length=max_length,
    )
    logger.info(
        "AssistantTurnDataCollator — response_ids: %s (decoded: %r)  end_ids: %s (decoded: %r)",
        response_ids,
        tokenizer.decode(response_ids),
        end_ids,
        tokenizer.decode(end_ids),
    )
    return collator


# ---------------------------------------------------------------------------
# Training arguments
# ---------------------------------------------------------------------------

def _build_sft_config(cfg: TrainingConfig, has_eval: bool = False) -> SFTConfig:
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

        # Memory — gradient checkpointing is essential for long sequences.
        # On the Unsloth path this is configured at get_peft_model time
        # (use_gradient_checkpointing="unsloth"); enabling it again here would
        # double-wrap the model, so it is dropped below when cfg.use_unsloth.
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

        # Evaluation — only enabled when caller passes an eval_dataset.
        eval_strategy=("epoch" if has_eval else "no"),
        per_device_eval_batch_size=cfg.per_device_batch_size,

        # Data loading
        dataloader_num_workers=4,
        dataloader_pin_memory=True,

        # Group sequences of similar length together to minimize padding waste.
        group_by_length=True,

        # SFT-specific
        dataset_text_field="text",
        packing=False,   # packing would interleave conversations — keep them separate
    )
    if cfg.use_unsloth:
        # Unsloth owns gradient checkpointing; let it manage the wrapping.
        kwargs.pop("gradient_checkpointing", None)
        kwargs.pop("gradient_checkpointing_kwargs", None)
        # Unsloth's SFTTrainer re-tokenizes the dataset with dataset_num_proc
        # workers, defaulting to (os.cpu_count()); on a 64-core node that
        # spawns 64 processes each loading the tokenizer and 10k-token texts,
        # which OOMs and one worker "abruptly dies" mid-map. Cap it low — the
        # SFT dataset is small (hundreds of examples), so the loss of
        # parallelism is negligible. Override with TOKENIZE_NUM_PROC if needed.
        kwargs["dataset_num_proc"] = int(os.environ.get("TOKENIZE_NUM_PROC", "2"))

    sft_params = inspect.signature(SFTConfig.__init__).parameters
    length_param = (
        "max_seq_length"
        if "max_seq_length" in sft_params
        else "max_length"
    )
    kwargs[length_param] = cfg.data.max_seq_length

    # Older transformers used `evaluation_strategy`; newer ones use `eval_strategy`.
    if "eval_strategy" not in sft_params and "evaluation_strategy" in sft_params:
        kwargs["evaluation_strategy"] = kwargs.pop("eval_strategy")

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
    eval_dataset: Dataset | None = None,
) -> SFTTrainer:
    """Build the SFTTrainer.  Caller is responsible for calling .train().

    If eval_dataset is provided, evaluation runs once per epoch and `eval_loss`
    (plus token-accuracy/entropy) is appended to trainer_state.json's
    log_history alongside training losses.
    """
    collator = _build_collator(tokenizer, cfg.data.max_seq_length)
    sft_cfg = _build_sft_config(cfg, has_eval=eval_dataset is not None)

    trainer = SFTTrainer(
        model=model,
        args=sft_cfg,
        train_dataset=dataset,
        eval_dataset=eval_dataset,
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
