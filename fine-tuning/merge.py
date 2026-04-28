#!/usr/bin/env python3
"""
Standalone script: merge a QLoRA adapter into the base model for vLLM.

Use this when you want to merge a previously trained adapter without re-running
train.py, or when you trained with --no-merge-after-training and now need a
merged model for inference.

Usage
─────
  python fine-tuning/merge.py \\
      --adapter-path /scratch/my-run \\
      --base-model   /home/hamedth/.../gemma4-4b \\
      --output-dir   /scratch/my-run-merged

After merging, serve with vLLM:
  VLLM_MODEL=/scratch/my-run-merged \\
  VLLM_ALIAS=my-finetuned-model \\
  ./evaluation_scripts/llm_eval/start_vllm.sh start
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from finetune.config import parse_merge_args
from finetune.merge import run_merge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)


def main() -> None:
    cfg = parse_merge_args()
    run_merge(cfg)


if __name__ == "__main__":
    main()
