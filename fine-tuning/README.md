# RepoBehave Fine-Tuning

This directory contains everything needed to (1) generate an SFT dataset from
repository QA instances and (2) fine-tune a small language model on that
dataset using QLoRA so it learns to answer code-behavior questions via
agentic tool use.

---

## Directory layout

```
fine-tuning/
├── README.md                     ← this file
├── create_sft_dataset.py         ← dataset generation script
├── sft_dataset/                  ← generated training data (git-ignored heavy files)
│   ├── Sympy/
│   │   ├── core_expand_mul_indirect_output.json
│   │   └── …
│   ├── faker_qa/
│   └── repo_cache/               ← Docker repo snapshots (local cache, not committed)
├── train.py                      ← QLoRA training entry point
├── merge.py                      ← standalone adapter-merge script
└── finetune/                     ← Python package
    ├── __init__.py
    ├── config.py                 ← dataclasses + CLI argument parsers
    ├── data.py                   ← dataset loading and chat-template formatting
    ├── model.py                  ← quantized model + LoRA setup
    ├── trainer.py                ← SFTTrainer construction with loss masking
    └── merge.py                  ← merge LoRA adapter into base model for vLLM
```

---

## 1 · Dataset generation (`create_sft_dataset.py`)

### What it does

For each QA instance in `qa_instances/<repo>/` the script:

1. Loads `oracle.json` (ground-truth answer) and `trace.log` (runtime execution trace).
2. Spins up a **teacher LLM** (default `gpt-5.4`) that privately knows the oracle
   answer and execution trace in its system prompt only.
3. Runs an **agentic loop** where the teacher uses `read_file` and `list_dir` to
   read source code and writes code-based reasoning (never quoting the trace).
4. Saves the conversation using an **oracle-free student system prompt** that
   matches the evaluation format exactly — so the saved training data is
   indistinguishable from evaluation trajectories.

The saved JSON has the schema:

```json
{
  "repo": "Sympy",
  "instance_id": "core_expand_mul_indirect_output",
  "question_kind": "program_state_prediction",
  "attempt": 1,
  "messages": [ … ]   // OpenAI-format multi-turn conversation
}
```

Each message follows the OpenAI API format:
- `system` / `user` / `assistant` roles
- `tool_calls` list in assistant messages (when calling a tool)
- `role: "tool"` messages with `tool_call_id`, `name`, `content` (tool results)

### Prerequisites

- Docker daemon running (to pull and snapshot repo images)
- An OpenAI API key in `.env`:  `openai_api_key=sk-proj-…`

### Commands

```bash
# Generate for all repos
python fine-tuning/create_sft_dataset.py

# Generate for specific repos
python fine-tuning/create_sft_dataset.py --repo Sympy faker_qa

# Generate specific instances within one repo
python fine-tuning/create_sft_dataset.py \
    --repo Sympy \
    --instances core_expand_mul_indirect_output

# Use a different model
python fine-tuning/create_sft_dataset.py --model gpt-4o --repo Sympy

# Force re-copy repo from Docker (bypasses local cache)
python fine-tuning/create_sft_dataset.py --repo Sympy --force-copy

# Parallel workers
python fine-tuning/create_sft_dataset.py --workers 8
```

### Key design decisions

| Decision | Reason |
|----------|--------|
| Oracle + trace in teacher system prompt only | Training data is oracle-free, matching evaluation |
| Trace never cited in assistant text | Model learns code reasoning, not trace lookup |
| `read_file` + `list_dir` only (no repo map) | Matches the evaluation tool set |
| Two attempts per instance; discard if both wrong | Ensures training data contains correct answers |

---

## 2 · QLoRA fine-tuning (`train.py`)

### Method: QLoRA

- **4-bit NF4 quantization** (bitsandbytes) compresses the frozen base model to
  ~2 GB VRAM for a 4 B parameter model.
- **LoRA adapters** (rank 16 by default) are applied to all linear projections
  in attention and MLP layers (~50 M trainable parameters).
- **Gradient checkpointing** recomputes activations on the backward pass to
  keep peak memory under control with long sequences.
- **Paged AdamW 8-bit** uses CPU offloading for optimizer states.

### Chat-template alignment

Training conversations are formatted with `tokenizer.apply_chat_template(
messages, tools=TOOLS)`.  This produces the **same token sequence** that vLLM
generates when it receives an API request with the same tools — so the model
sees exactly its inference distribution during training.

### Loss masking

`DataCollatorForCompletionOnlyLM` masks system prompts, user turns, and tool
responses, computing loss **only on assistant (model) turns**.  This includes:

- Intermediate exploration messages (explaining which code was read and why)
- The final JSON answer

### Hardware requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU VRAM  | 24 GB (batch=1, seq=4096) | 80 GB A100 (batch=1, seq=8192) |
| RAM       | 32 GB  | 64 GB |
| Storage   | 20 GB for base model + adapters | 100 GB if merging |

### Commands

```bash
# Basic — train on all repos, save adapter
python fine-tuning/train.py \
    --model /home/hamedth/projects/.../gemma4-4b \
    --output-dir /scratch/runs/gemma4-repobehave

# Specific repos
python fine-tuning/train.py \
    --model /home/hamedth/projects/.../gemma4-4b \
    --output-dir /scratch/runs/gemma4-repobehave \
    --repos Sympy faker_qa matplotlib_qa pydata_xarray

# Higher LoRA rank for better capacity
python fine-tuning/train.py \
    --model /home/hamedth/projects/.../gemma4-4b \
    --output-dir /scratch/runs/gemma4-r64 \
    --lora-r 64 --lora-alpha 128

# Train and immediately merge for vLLM
python fine-tuning/train.py \
    --model /home/hamedth/projects/.../gemma4-4b \
    --output-dir /scratch/runs/gemma4-repobehave \
    --merge-after-training \
    --merged-output-dir /scratch/runs/gemma4-repobehave-merged

# Full help
python fine-tuning/train.py --help
```

### Key hyperparameters

| Flag | Default | Notes |
|------|---------|-------|
| `--lora-r` | 16 | Rank; 16 is good for ~400 examples, 64 for larger datasets |
| `--lora-alpha` | 32 | Scaling = alpha / r; keep ratio = 2 |
| `--epochs` | 2 | 1–3 epochs typical for SFT |
| `--batch-size` | 1 | Per device; increase only if VRAM allows |
| `--grad-accum` | 32 | Effective batch = batch-size × grad-accum |
| `--lr` | 2e-4 | Standard QLoRA learning rate |
| `--max-seq-length` | 16384 | Tool-call conversations are long; truncation at this length |
| `--optim` | `paged_adamw_8bit` | Required for QLoRA memory efficiency |

### Output layout after training

```
<output-dir>/
├── adapter_config.json         ← LoRA hyperparameters
├── adapter_model.safetensors   ← trained ΔW weights
├── tokenizer_config.json
├── tokenizer.model
└── checkpoint-<N>/             ← intermediate checkpoints
```

---

## 3 · Merging adapters for vLLM (`merge.py`)

vLLM loads a standard HuggingFace model directory.  Before serving the
fine-tuned model you must merge the LoRA adapter back into the base weights.

```bash
python fine-tuning/merge.py \
    --adapter-path /scratch/runs/gemma4-repobehave \
    --base-model   /home/hamedth/projects/.../gemma4-4b \
    --output-dir   /scratch/runs/gemma4-repobehave-merged
```

The merge runs in `bfloat16` by default.  No GPU is needed (but it is faster
with one).  The output directory is a normal HuggingFace model directory.

---

## 4 · Serving and evaluating the fine-tuned model

### Start vLLM

```bash
export VLLM_MODEL=/scratch/runs/gemma4-repobehave-merged
export VLLM_ALIAS=gemma4-repobehave
./evaluation_scripts/llm_eval/start_vllm.sh start
```

The existing `start_vllm.sh` already sets `VLLM_TOOL_CALL_PARSER=gemma4` and
`VLLM_ENABLE_AUTO_TOOL_CHOICE=1`, so the merged model will handle tool calls
correctly out of the box.

### Run evaluation

```bash
python evaluation_scripts/llm_eval/run_llm_repomap_eval_host.py \
    --provider vllm \
    --model gemma4-repobehave \
    --repo-map-mode none \
    --repo Sympy
```

This is identical to how the base model is evaluated, making results directly
comparable.

---

## 5 · Environment setup

All dependencies are in the root `environment.yml`.  Fine-tuning requires
these additional packages (already added):

| Package | Version | Purpose |
|---------|---------|---------|
| `bitsandbytes` | ≥ 0.44 | 4-bit NF4 quantization |
| `peft` | ≥ 0.15 | LoRA adapters |
| `trl` | ≥ 0.17 | SFTTrainer + DataCollatorForCompletionOnlyLM |
| `accelerate` | ≥ 1.3 | Device placement + mixed precision |
| `wandb` | ≥ 0.19 | Experiment tracking (optional) |

```bash
# Create or update the Triad conda environment
conda env update -f environment.yml --prune
```

> **bitsandbytes on a cluster GPU node:**  If the generic `bitsandbytes` wheel
> does not detect your CUDA version, install the CUDA-specific build:
> ```bash
> pip install bitsandbytes \
>     --index-url https://huggingface.github.io/bitsandbytes-cuda-versions/
> ```

---

## 6 · Typical SLURM job script

```bash
#!/usr/bin/env bash
#SBATCH --job-name=gemma4-qlora
#SBATCH --gres=gpu:a100:1
#SBATCH --mem=80G
#SBATCH --cpus-per-task=8
#SBATCH --time=12:00:00
#SBATCH --output=logs/%j.out

module load StdEnv/2023
conda activate Triad

python fine-tuning/train.py \
    --model /home/hamedth/projects/def-hemmati-ac/hamedth/hugging_face/gemma4-4b \
    --output-dir "$SCRATCH/runs/gemma4-repobehave-$SLURM_JOB_ID" \
    --repos Sympy faker_qa matplotlib_qa pydata_xarray yt_dlp \
    --lora-r 16 \
    --epochs 2 \
    --merge-after-training
```
