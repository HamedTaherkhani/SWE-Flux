"""Training and merge configuration dataclasses with CLI argument parsers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

# ---------------------------------------------------------------------------
# Default LoRA target modules for Gemma / Llama-style architectures.
# Covers all linear projections in attention (q/k/v/o) and MLP (gate/up/down).
# ---------------------------------------------------------------------------
_DEFAULT_TARGET_MODULES: List[str] = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]

# Gemma 4 4B is multimodal: only the *vision/audio* towers use
# Gemma4ClippableLinear (a wrapper whose .linear inner module PEFT can target).
# The language model's projections are plain bnb Linear4bit. The previous
# suffix list "q_proj.linear" matched ONLY the vision tower — LoRA attached
# there never participates in text-only forward, so gradients are always None
# and training silently no-ops. Use a regex anchored to language_model.* so
# LoRA grafts onto the text decoder's projections instead.
GEMMA4_4B_TARGET_MODULES: str = (
    r".*language_model\..*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)$"
)


def _default_target_modules_for_model(model_path: str):
    """Return target_modules for PEFT — either a list (suffix match) or a regex string."""
    model_name = Path(model_path).name.lower()
    if model_name == "gemma4-4b":
        return GEMMA4_4B_TARGET_MODULES  # regex string, must NOT be wrapped in list()
    return list(_DEFAULT_TARGET_MODULES)


# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------

@dataclass
class LoraConfig:
    r: int = 16
    alpha: int = 32
    dropout: float = 0.05
    # Either a list of suffix strings (matched via str.endswith) or a single
    # regex string. Gemma 4 uses the regex form to scope LoRA to the language
    # model only and skip the multimodal vision/audio towers.
    target_modules: Union[List[str], str] = field(
        default_factory=lambda: list(_DEFAULT_TARGET_MODULES)
    )
    bias: str = "none"


@dataclass
class QuantizationConfig:
    load_in_4bit: bool = True
    quant_type: str = "nf4"           # NF4 is the QLoRA recommendation
    double_quant: bool = True         # nested quantization — saves ~0.4 bits/param
    compute_dtype: str = "bfloat16"   # compute in bf16, store in 4-bit


@dataclass
class DataConfig:
    dataset_dir: Path
    repos: Optional[List[str]]  # None → all repos present in dataset_dir
    max_seq_length: int = 16384


@dataclass
class TrainingConfig:
    # --- Required ---
    model_path: str
    output_dir: Path
    data: DataConfig
    lora: LoraConfig = field(default_factory=LoraConfig)
    quant: QuantizationConfig = field(default_factory=QuantizationConfig)

    # --- Training hyperparameters ---
    num_epochs: int = 2
    per_device_batch_size: int = 1
    gradient_accumulation_steps: int = 32   # effective batch ≈ 32 on 80 GB
    learning_rate: float = 2e-4
    lr_scheduler: str = "cosine"
    warmup_ratio: float = 0.05
    max_grad_norm: float = 0.3
    weight_decay: float = 0.001
    optim: str = "paged_adamw_8bit"          # 8-bit Adam — critical for memory

    # --- Logging / checkpointing ---
    logging_steps: int = 10
    save_steps: int = 100
    save_total_limit: int = 3
    report_to: str = "none"                  # set to "wandb" for experiment tracking

    # --- Post-training merge ---
    merge_after_training: bool = False
    merged_output_dir: Optional[Path] = None


@dataclass
class MergeConfig:
    adapter_path: Path
    base_model: str
    output_dir: Path
    dtype: str = "bfloat16"


# ---------------------------------------------------------------------------
# CLI parsers
# ---------------------------------------------------------------------------

def parse_train_args(argv: Optional[List[str]] = None) -> TrainingConfig:
    parser = argparse.ArgumentParser(
        description="QLoRA fine-tuning for RepoBehave tool-use trajectories",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # --- Required ---
    parser.add_argument(
        "--model", required=True, metavar="PATH_OR_ID",
        help=(
            "HuggingFace model path or ID. "
            "Example: /home/hamedth/.../gemma4-4b  or  google/gemma-4-E4B"
        ),
    )
    parser.add_argument(
        "--output-dir", required=True, type=Path, metavar="DIR",
        help="Directory to write LoRA checkpoints and final adapter",
    )

    # --- Data ---
    _default_dataset = Path(__file__).resolve().parent.parent / "sft_dataset"
    parser.add_argument(
        "--dataset-dir", type=Path, default=_default_dataset, metavar="DIR",
        help="Root of the sft_dataset directory",
    )
    parser.add_argument(
        "--repos", nargs="*", metavar="REPO",
        help="Repo names to train on (default: all repos found in --dataset-dir)",
    )
    parser.add_argument(
        "--max-seq-length", type=int, default=16384,
        help="Maximum token length per training example (longer examples are truncated)",
    )

    # --- LoRA ---
    lora = parser.add_argument_group("LoRA")
    lora.add_argument("--lora-r", type=int, default=16, metavar="R",
                      help="LoRA rank")
    lora.add_argument("--lora-alpha", type=int, default=32, metavar="A",
                      help="LoRA alpha (scaling = alpha / r)")
    lora.add_argument("--lora-dropout", type=float, default=0.05)
    lora.add_argument(
        "--lora-target-modules", nargs="+", default=None,
        metavar="MODULE",
        help="Linear layer names to apply LoRA adapters to",
    )

    # --- Quantization ---
    quant = parser.add_argument_group("Quantization")
    quant.add_argument("--no-4bit", action="store_true",
                       help="Disable 4-bit quantization (train in full bf16)")
    quant.add_argument("--compute-dtype", default="bfloat16",
                       choices=["bfloat16", "float16"],
                       help="Dtype used for forward/backward computation")

    # --- Training hyperparameters ---
    train = parser.add_argument_group("Training")
    train.add_argument("--epochs", type=int, default=2)
    train.add_argument("--batch-size", type=int, default=1,
                       help="Per-device training batch size")
    train.add_argument("--grad-accum", type=int, default=32,
                       help="Gradient accumulation steps (effective batch = batch-size × grad-accum)")
    train.add_argument("--lr", type=float, default=2e-4,
                       help="Peak learning rate")
    train.add_argument("--lr-scheduler", default="cosine",
                       choices=["cosine", "linear", "constant", "constant_with_warmup"])
    train.add_argument("--warmup-ratio", type=float, default=0.05)
    train.add_argument("--weight-decay", type=float, default=0.001)
    train.add_argument("--max-grad-norm", type=float, default=0.3)
    train.add_argument(
        "--optim", default="paged_adamw_8bit",
        choices=["adamw_torch", "paged_adamw_8bit", "paged_adamw_32bit"],
        help="Optimizer (paged_adamw_8bit is strongly recommended for QLoRA)",
    )

    # --- Logging / saving ---
    log = parser.add_argument_group("Logging and saving")
    log.add_argument("--logging-steps", type=int, default=10)
    log.add_argument("--save-steps", type=int, default=100)
    log.add_argument("--save-total-limit", type=int, default=3)
    log.add_argument("--report-to", default="none",
                     choices=["none", "wandb", "tensorboard"],
                     help="Experiment tracking backend")

    # --- Post-training ---
    post = parser.add_argument_group("Post-training")
    post.add_argument(
        "--merge-after-training", action="store_true",
        help="After training, merge LoRA weights into the base model and save for vLLM",
    )
    post.add_argument(
        "--merged-output-dir", type=Path, default=None, metavar="DIR",
        help="Where to write the merged model (default: <output-dir>-merged)",
    )

    args = parser.parse_args(argv)

    lora_cfg = LoraConfig(
        r=args.lora_r,
        alpha=args.lora_alpha,
        dropout=args.lora_dropout,
        target_modules=(
            args.lora_target_modules
            if args.lora_target_modules is not None
            else _default_target_modules_for_model(args.model)
        ),
    )
    quant_cfg = QuantizationConfig(
        load_in_4bit=not args.no_4bit,
        compute_dtype=args.compute_dtype,
    )
    data_cfg = DataConfig(
        dataset_dir=args.dataset_dir,
        repos=args.repos if args.repos else None,
        max_seq_length=args.max_seq_length,
    )

    merged_dir: Optional[Path] = args.merged_output_dir
    if args.merge_after_training and merged_dir is None:
        merged_dir = args.output_dir.parent / (args.output_dir.name + "-merged")

    return TrainingConfig(
        model_path=args.model,
        output_dir=args.output_dir,
        data=data_cfg,
        lora=lora_cfg,
        quant=quant_cfg,
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
        merged_output_dir=merged_dir,
    )


def parse_merge_args(argv: Optional[List[str]] = None) -> MergeConfig:
    parser = argparse.ArgumentParser(
        description="Merge a QLoRA adapter into the base model for vLLM inference",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--adapter-path", type=Path, required=True,
        help="Path to the trained PEFT adapter directory (output of train.py)",
    )
    parser.add_argument(
        "--base-model", required=True,
        help="Base model path or HF ID used during training",
    )
    parser.add_argument(
        "--output-dir", type=Path, required=True,
        help="Output directory for the merged model",
    )
    parser.add_argument(
        "--dtype", default="bfloat16", choices=["bfloat16", "float16"],
        help="Weight dtype of the merged model",
    )
    args = parser.parse_args(argv)
    return MergeConfig(
        adapter_path=args.adapter_path,
        base_model=args.base_model,
        output_dir=args.output_dir,
        dtype=args.dtype,
    )
