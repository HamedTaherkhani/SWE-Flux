#!/usr/bin/env python3
"""
RepoBehave QLoRA fine-tuning — main entry point.

Usage examples
──────────────

Train on all repos (default):
  python fine-tuning/train.py \\
      --model /home/hamedth/.../gemma4-4b \\
      --output-dir /scratch/my-run

Train on specific repos with higher rank:
  python fine-tuning/train.py \\
      --model /home/hamedth/.../gemma4-4b \\
      --output-dir /scratch/my-run \\
      --repos Sympy faker_qa matplotlib_qa \\
      --lora-r 64 --lora-alpha 128

Train and immediately merge for vLLM:
  python fine-tuning/train.py \\
      --model /home/hamedth/.../gemma4-4b \\
      --output-dir /scratch/my-run \\
      --merge-after-training \\
      --merged-output-dir /scratch/my-run-merged

Run help:
  python fine-tuning/train.py --help
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Make the finetune package importable regardless of working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Unsloth must be imported before transformers/trl for its monkeypatches to
# take effect. Do it here, gated on the CLI flag, so the default path never
# pulls in Unsloth.
if "--use-unsloth" in sys.argv:
    import unsloth  # noqa: F401

from finetune.config import parse_train_args
from finetune.data import build_dataset, dataset_stats
from finetune.model import load_model_and_tokenizer, load_tokenizer
from finetune.trainer import build_trainer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    cfg = parse_train_args()

    # Print a clear summary so the job log is self-documenting.
    logger.info("=" * 64)
    logger.info("RepoBehave QLoRA Fine-Tuning")
    logger.info("=" * 64)
    logger.info("  Model            : %s", cfg.model_path)
    logger.info("  Output           : %s", cfg.output_dir)
    logger.info("  Dataset          : %s", cfg.data.dataset_dir)
    logger.info("  Repos            : %s", cfg.data.repos or "all")
    logger.info("  LoRA rank / alpha: %d / %d", cfg.lora.r, cfg.lora.alpha)
    logger.info("  Quantization     : %s", "4-bit NF4" if cfg.quant.load_in_4bit else "none (bf16)")
    logger.info("  Epochs           : %d", cfg.num_epochs)
    logger.info(
        "  Batch            : %d × %d accumulation (effective = %d)",
        cfg.per_device_batch_size,
        cfg.gradient_accumulation_steps,
        cfg.per_device_batch_size * cfg.gradient_accumulation_steps,
    )
    logger.info("  Max seq length   : %d tokens", cfg.data.max_seq_length)
    logger.info("  Optimizer        : %s  lr=%g", cfg.optim, cfg.learning_rate)
    logger.info("  Backend          : %s", "Unsloth FastModel" if cfg.use_unsloth else "transformers + bnb + PEFT")
    logger.info("  Merge after      : %s", cfg.merge_after_training)
    logger.info("=" * 64)

    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: tokenizer (and model, on the Unsloth path) ───────────────────
    # Unsloth loads the model and tokenizer together; reuse its tokenizer for
    # dataset formatting so a single tokenizer drives chat-templating, the
    # collator's boundary discovery, and the model.
    model = None
    if cfg.use_unsloth:
        logger.info("[1/4] Loading model + tokenizer via Unsloth FastModel from %s ...", cfg.model_path)
        from finetune.unsloth_model import load_model_and_tokenizer_unsloth
        model, tokenizer = load_model_and_tokenizer_unsloth(
            cfg.model_path, cfg.lora, cfg.quant, cfg.data.max_seq_length
        )
    else:
        logger.info("[1/4] Loading tokenizer from %s ...", cfg.model_path)
        tokenizer = load_tokenizer(cfg.model_path)

    # ── Step 2: dataset ──────────────────────────────────────────────────────
    logger.info("[2/4] Building and formatting dataset ...")
    dataset = build_dataset(cfg.data, tokenizer)
    dataset_stats(dataset, tokenizer, cfg.data.max_seq_length)

    # ── Step 3: model ────────────────────────────────────────────────────────
    if model is None:
        logger.info("[3/4] Loading model with QLoRA ...")
        model, _ = load_model_and_tokenizer(cfg.model_path, cfg.lora, cfg.quant)
    else:
        logger.info("[3/4] Model already loaded via Unsloth.")

    # ── Step 4: train ────────────────────────────────────────────────────────
    logger.info("[4/4] Building trainer and starting training ...")
    trainer = build_trainer(cfg, model, tokenizer, dataset)
    trainer.train()

    logger.info("Training finished.  Saving adapter to %s ...", cfg.output_dir)
    trainer.save_model(str(cfg.output_dir))
    tokenizer.save_pretrained(str(cfg.output_dir))
    logger.info("Adapter saved.")

    # ── Optional: merge for vLLM ─────────────────────────────────────────────
    if cfg.merge_after_training:
        logger.info("Merging LoRA into base model for vLLM ...")
        from finetune.merge import merge_adapter
        merge_adapter(
            adapter_path=cfg.output_dir,
            base_model=cfg.model_path,
            output_dir=cfg.merged_output_dir,
            dtype=cfg.quant.compute_dtype,
        )
        logger.info("Merged model saved to %s", cfg.merged_output_dir)

    logger.info("All done.")


if __name__ == "__main__":
    main()
