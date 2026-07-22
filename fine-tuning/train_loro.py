#!/usr/bin/env python3
"""
Leave-one-repo-out (LORO) QLoRA fine-tuning for RepoBehave.

For each repo R in --dataset-dir:
  • train on the other 8 repos
  • evaluate on R after every epoch (eval_loss + token metrics logged)
  • save a LoRA adapter to <output_root>/loro-<R>/
  • optionally merge into a full bf16 model at <output_root>/loro-<R>-merged/
    (use this with vLLM in evaluate_loro.sh)
  • dump the full metric history to <output_root>/loro-<R>/metrics.json

Usage
─────
  python fine-tuning/train_loro.py \\
    --model /path/to/gemma4-4b \\
    --output-root /scratch/loro-runs \\
    --batch-size 1 --grad-accum 32 --max-seq-length 8192 \\
    --epochs 2 --logging-steps 1 --merge-after-training

Single-fold debugging:
  python fine-tuning/train_loro.py ... --only-repo Sympy
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

# Make the finetune package importable regardless of working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Unsloth must be imported before transformers/trl for its monkeypatches to
# take effect. Gate on the CLI flag so the default path never pulls in Unsloth.
if "--use-unsloth" in sys.argv:
    import unsloth  # noqa: F401

import torch  # noqa: E402

from finetune.config import (  # noqa: E402
    DataConfig,
    LoraConfig,
    QuantizationConfig,
    TrainingConfig,
    _default_target_modules_for_model,
)
from finetune.data import build_dataset, dataset_stats  # noqa: E402
from finetune.model import load_model_and_tokenizer, load_tokenizer  # noqa: E402
from finetune.trainer import build_trainer  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train_loro")

_NON_REPO_DIRS = {"repo_cache"}


def _discover_repos(dataset_dir: Path) -> List[str]:
    return sorted(
        d.name
        for d in dataset_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".") and d.name not in _NON_REPO_DIRS
    )


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Leave-one-repo-out QLoRA fine-tuning",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--model", required=True, metavar="PATH",
                   help="Base model path or HF id (e.g. /…/gemma4-4b)")
    p.add_argument("--output-root", required=True, type=Path, metavar="DIR",
                   help="Root directory; each fold writes to <output-root>/loro-<repo>/")

    _default_dataset = Path(__file__).resolve().parent / "sft_dataset"
    p.add_argument("--dataset-dir", type=Path, default=_default_dataset, metavar="DIR")
    p.add_argument("--only-repo", default=None, metavar="REPO",
                   help="Run a single fold (skip the other 8). Useful for debugging.")
    p.add_argument("--skip-existing", action="store_true",
                   help="Skip a fold if <output-root>/loro-<repo>/adapter_config.json exists.")

    p.add_argument("--max-seq-length", type=int, default=8192)
    p.add_argument("--max-seq-length-override", action="append", default=[],
                   metavar="REPO=N",
                   help="Per-fold max-seq-length override, e.g. --max-seq-length-override cfnlint_qa=6144. "
                        "Repeatable. Applies when REPO is the held-out fold.")

    lora = p.add_argument_group("LoRA")
    lora.add_argument("--lora-r", type=int, default=16)
    lora.add_argument("--lora-alpha", type=int, default=32)
    lora.add_argument("--lora-dropout", type=float, default=0.05)

    p.add_argument("--no-4bit", action="store_true")
    p.add_argument("--compute-dtype", default="bfloat16",
                   choices=["bfloat16", "float16"])

    tr = p.add_argument_group("Training")
    tr.add_argument("--epochs", type=int, default=2)
    tr.add_argument("--batch-size", type=int, default=1)
    tr.add_argument("--grad-accum", type=int, default=32)
    tr.add_argument("--lr", type=float, default=2e-4)
    tr.add_argument("--lr-scheduler", default="cosine",
                    choices=["cosine", "linear", "constant", "constant_with_warmup"])
    tr.add_argument("--warmup-ratio", type=float, default=0.05)
    tr.add_argument("--weight-decay", type=float, default=0.001)
    tr.add_argument("--max-grad-norm", type=float, default=0.3)
    tr.add_argument("--optim", default="paged_adamw_8bit",
                    choices=["adamw_torch", "paged_adamw_8bit", "paged_adamw_32bit"])

    p.add_argument("--logging-steps", type=int, default=1)
    p.add_argument("--save-steps", type=int, default=10_000,
                   help="Set high to skip mid-training checkpoint dirs; "
                        "the final adapter is always saved.")
    p.add_argument("--save-total-limit", type=int, default=1)
    p.add_argument("--report-to", default="none",
                   choices=["none", "wandb", "tensorboard"])

    p.add_argument("--merge-after-training", action="store_true",
                   help="Also write a merged bf16 model to "
                        "<output-root>/loro-<repo>-merged/ for vLLM serving.")

    p.add_argument("--use-unsloth", action="store_true",
                   help="Load the model + LoRA via Unsloth FastModel for a "
                        "larger context window. Hyperparameters and the "
                        "training loop are unchanged.")
    p.add_argument("--final-answer-only-loss", action="store_true",
                   help="Compute SFT loss only on the final reasoning/answer "
                        "assistant turn (the turn containing '## Answer'). "
                        "Earlier assistant tool calls and tool responses are "
                        "kept as context but masked from training.")

    return p.parse_args()


def _parse_seq_overrides(items: List[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--max-seq-length-override expects REPO=N, got {item!r}")
        repo, value = item.split("=", 1)
        out[repo.strip()] = int(value)
    return out


def _build_cfg_for_fold(args: argparse.Namespace, held_out: str, train_repos: List[str],
                        output_dir: Path, max_seq_length: int) -> TrainingConfig:
    return TrainingConfig(
        model_path=args.model,
        output_dir=output_dir,
        data=DataConfig(
            dataset_dir=args.dataset_dir,
            repos=train_repos,
            max_seq_length=max_seq_length,
        ),
        lora=LoraConfig(
            r=args.lora_r,
            alpha=args.lora_alpha,
            dropout=args.lora_dropout,
            target_modules=_default_target_modules_for_model(args.model),
        ),
        quant=QuantizationConfig(
            load_in_4bit=not args.no_4bit,
            compute_dtype=args.compute_dtype,
        ),
        num_epochs=args.epochs,
        per_device_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler=args.lr_scheduler,
        warmup_ratio=args.warmup_ratio,
        max_grad_norm=args.max_grad_norm,
        weight_decay=args.weight_decay,
        optim=args.optim,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=args.save_total_limit,
        report_to=args.report_to,
        merge_after_training=args.merge_after_training,
        merged_output_dir=(
            output_dir.parent / f"{output_dir.name}-merged"
            if args.merge_after_training else None
        ),
        use_unsloth=args.use_unsloth,
        final_answer_only_loss=args.final_answer_only_loss,
    )


def _dump_metrics(trainer, output_dir: Path, held_out: str) -> None:
    """Persist trainer_state.log_history to a friendly JSON (per-fold)."""
    history = list(getattr(trainer.state, "log_history", []) or [])
    metrics_path = output_dir / "metrics.json"
    payload = {
        "held_out_repo": held_out,
        "global_step": int(getattr(trainer.state, "global_step", 0)),
        "epoch": float(getattr(trainer.state, "epoch", 0.0) or 0.0),
        "log_history": history,
    }
    metrics_path.write_text(json.dumps(payload, indent=2, default=str))
    eval_losses = [h["eval_loss"] for h in history if "eval_loss" in h]
    if eval_losses:
        logger.info("  → eval_loss per epoch: %s",
                    [f"{x:.4f}" for x in eval_losses])
    logger.info("  → metrics saved to %s", metrics_path)


def _run_fold(args: argparse.Namespace, held_out: str, all_repos: List[str],
              seq_overrides: dict[str, int]) -> None:
    train_repos = [r for r in all_repos if r != held_out]
    fold_dir = args.output_root / f"loro-{held_out}"

    if args.skip_existing and (fold_dir / "adapter_config.json").exists():
        logger.info("[skip] fold for held-out=%s already complete at %s",
                    held_out, fold_dir)
        return

    max_seq_length = seq_overrides.get(held_out, args.max_seq_length)
    if max_seq_length != args.max_seq_length:
        logger.info("Per-fold override: max_seq_length=%d for held-out=%s (default %d)",
                    max_seq_length, held_out, args.max_seq_length)

    fold_dir.mkdir(parents=True, exist_ok=True)
    cfg = _build_cfg_for_fold(args, held_out, train_repos, fold_dir, max_seq_length)
    if cfg.final_answer_only_loss:
        print(
            "LOSS MODE: final-answer-only "
            "(only assistant turns containing '## Answer' receive labels)",
            flush=True,
        )

    logger.info("=" * 72)
    logger.info("FOLD: held-out=%s   train_repos=%s", held_out, train_repos)
    logger.info("Output dir: %s", fold_dir)
    logger.info("=" * 72)

    # Unsloth loads model + tokenizer together; reuse its tokenizer so a single
    # tokenizer drives chat-templating, the collator, and the model.
    model = None
    if cfg.use_unsloth:
        from finetune.unsloth_model import load_model_and_tokenizer_unsloth
        model, tokenizer = load_model_and_tokenizer_unsloth(
            cfg.model_path, cfg.lora, cfg.quant, cfg.data.max_seq_length
        )
        _text_cfg = getattr(model.config, "text_config", model.config)
        print(
            "MODEL CONFIG: num_kv_shared_layers="
            f"{getattr(_text_cfg, 'num_kv_shared_layers', None)}",
            flush=True,
        )
    else:
        tokenizer = load_tokenizer(cfg.model_path)

    train_ds = build_dataset(cfg.data, tokenizer)
    dataset_stats(train_ds, tokenizer, cfg.data.max_seq_length)

    eval_data_cfg = DataConfig(
        dataset_dir=args.dataset_dir,
        repos=[held_out],
        max_seq_length=max_seq_length,
    )
    eval_ds = build_dataset(eval_data_cfg, tokenizer)
    logger.info("Eval set (held-out=%s): %d examples", held_out, len(eval_ds))

    if model is None:
        model, _ = load_model_and_tokenizer(cfg.model_path, cfg.lora, cfg.quant)

    trainer = build_trainer(cfg, model, tokenizer, train_ds, eval_dataset=eval_ds)
    trainer.train()

    logger.info("Saving adapter to %s ...", fold_dir)
    trainer.save_model(str(fold_dir))
    tokenizer.save_pretrained(str(fold_dir))

    _dump_metrics(trainer, fold_dir, held_out)

    if args.merge_after_training:
        merged_dir = cfg.merged_output_dir
        assert merged_dir is not None
        logger.info("Merging LoRA into base for vLLM serving → %s", merged_dir)
        from finetune.merge import merge_adapter
        merge_adapter(
            adapter_path=fold_dir,
            base_model=cfg.model_path,
            output_dir=merged_dir,
            dtype=cfg.quant.compute_dtype,
        )

    # Release GPU memory before the next fold.
    del trainer, model, tokenizer, train_ds, eval_ds
    gc.collect()
    torch.cuda.empty_cache()


def main() -> None:
    args = _parse_args()
    args.output_root = args.output_root.resolve()
    args.output_root.mkdir(parents=True, exist_ok=True)

    seq_overrides = _parse_seq_overrides(args.max_seq_length_override)
    if seq_overrides:
        logger.info("Per-fold max_seq_length overrides: %s", seq_overrides)

    all_repos = _discover_repos(args.dataset_dir)
    if not all_repos:
        raise SystemExit(f"No repos found in {args.dataset_dir}")
    logger.info("Discovered %d repos: %s", len(all_repos), all_repos)

    if args.only_repo is not None:
        if args.only_repo not in all_repos:
            raise SystemExit(f"--only-repo={args.only_repo!r} not in {all_repos}")
        folds = [args.only_repo]
    else:
        folds = all_repos

    summary_path = args.output_root / "loro_summary.json"
    summary = {"folds": []}

    for i, held_out in enumerate(folds, start=1):
        logger.info("\n[%d/%d] Starting fold for held-out repo: %s",
                    i, len(folds), held_out)
        _run_fold(args, held_out, all_repos, seq_overrides)

        # Append a brief summary line per fold so the JSON is updated incrementally.
        metrics_path = args.output_root / f"loro-{held_out}" / "metrics.json"
        if metrics_path.exists():
            data = json.loads(metrics_path.read_text())
            eval_losses = [h["eval_loss"] for h in data["log_history"] if "eval_loss" in h]
            train_losses = [h["loss"] for h in data["log_history"] if "loss" in h]
            summary["folds"].append({
                "held_out": held_out,
                "train_loss_final": train_losses[-1] if train_losses else None,
                "eval_loss_per_epoch": eval_losses,
            })
            summary_path.write_text(json.dumps(summary, indent=2))

    logger.info("All folds done. Summary written to %s", summary_path)


if __name__ == "__main__":
    main()
