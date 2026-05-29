# RepoBehave Fine-Tuning

Generate an SFT dataset from RepoBehave QA instances, fine-tune a small LM with
QLoRA, and evaluate it via vLLM. Single-model training (`train.py`) and
leave-one-repo-out (`train_loro.py`) are both supported.

---

## Environment

Use `fine-tuning/environment.yml` (env name `RepoBehave_finetune`). The root
`environment.yml` (`Triad_env`) is for evaluation and vLLM serving.

```bash
conda env create --solver libmamba -f fine-tuning/environment.yml
conda activate RepoBehave_finetune
```

Then install Flash Attention (must match the cluster CUDA / torch ABI):

```bash
pip install "flash-attn>=2.7" --no-build-isolation
```

Verify GPU stack:

```bash
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

---

## Layout

```
fine-tuning/
├── README.md
├── environment.yml
├── create_sft_dataset.py           generate trajectories from QA instances
├── train.py                        single-model QLoRA training
├── train_loro.py                   leave-one-repo-out: 9 models, one per fold
├── evaluate_loro.sh                run vLLM evaluation across LORO folds
├── merge.py                        merge adapter into base for vLLM
├── fsdp_qlora.yaml                 accelerate FSDP config (multi-GPU, see note below)
├── sft_dataset/                    generated training data
└── finetune/                       package: config / data / model / trainer / merge
```

---

## 1 · Generate the SFT dataset

For each `qa_instances/<repo>/<instance>` a teacher LLM (default `gpt-5.4`)
uses `read_file` and `list_dir` to derive the answer from source code, with the
oracle answer kept in the teacher's system prompt only. The saved JSON has the
schema:

```json
{ "repo": "Sympy", "instance_id": "...", "messages": [ ... ] }
```

The student system prompt and tool set match what vLLM sees at evaluation
time, so training and inference distributions stay identical.

Requirements: Docker daemon running, `openai_api_key=...` in `.env`.

```bash
python fine-tuning/create_sft_dataset.py                              # all repos
python fine-tuning/create_sft_dataset.py --repo Sympy faker_qa        # subset
python fine-tuning/create_sft_dataset.py --workers 8                  # parallel
```

---

## 2 · Train one model

```bash
FORCE_ATTN_IMPL=sdpa CUDA_VISIBLE_DEVICES=0 python fine-tuning/train.py \
  --model /path/to/gemma4-4b \
  --output-dir /scratch/runs/gemma4-r64 \
  --batch-size 1 --grad-accum 32 \
  --max-seq-length 8192 \
  --epochs 2 --logging-steps 1
```

Useful flags:

| Flag | Default | Notes |
|---|---|---|
| `--lora-r` / `--lora-alpha` | 16 / 32 | keep ratio 2 |
| `--max-seq-length` | 16384 | **For Gemma 4 4B on this stack, use 8192 or 12288.** See "Known footguns". With `--use-unsloth` you can push this much higher on an H100. |
| `--repos` | all | restrict to a subset |
| `--merge-after-training` | off | also write a bf16 merged model for vLLM |
| `--use-unsloth` | off | load the model + LoRA via Unsloth FastModel for a larger context window. See "Unsloth backend". |

After training, `<output-dir>/` contains `adapter_config.json` +
`adapter_model.safetensors`. With `--merge-after-training`, a full bf16 model
is written to `<output-dir>-merged/`.

---

## 3 · Leave-one-repo-out (LORO)

Trains 9 models (one per repo), each on the other 8, evaluating per-epoch on
the held-out repo.

```bash
FORCE_ATTN_IMPL=sdpa CUDA_VISIBLE_DEVICES=0 python fine-tuning/train_loro.py \
  --model /path/to/gemma4-4b \
  --output-root /scratch/loro \
  --batch-size 1 --grad-accum 32 \
  --max-seq-length 8192 \
  --epochs 2 --logging-steps 1 \
  --merge-after-training
```

Smoke test a single fold first: `--only-repo Sympy`. Resume after interruption:
`--skip-existing`.

Output per fold:

```
/scratch/loro/loro-<repo>/         adapter + tokenizer + metrics.json
/scratch/loro/loro-<repo>-merged/  bf16 standalone model for vLLM
/scratch/loro/loro_summary.json    rolling summary across folds
```

`metrics.json` contains the full `trainer_state.log_history` — train loss every
step, eval_loss per epoch, plus token-accuracy / entropy / grad_norm.

---

## 4 · Evaluation (vLLM)

Single trained model: start vLLM, then call the existing eval driver.

```bash
export VLLM_MODEL=/scratch/runs/gemma4-r64-merged
export VLLM_ALIAS=gemma4-r64
./evaluation_scripts/llm_eval/start_vllm.sh start

python evaluation_scripts/llm_eval/run_llm_repomap_eval_host.py \
  --provider vllm --model $VLLM_ALIAS \
  --repo Sympy --repo-map-mode none
```

LORO (all 9 folds): each fold is served, evaluated on its own held-out repo,
then torn down. Outputs land under `fine-tuning/evaluations/`.

```bash
LORO_RUNS_ROOT=/scratch/loro fine-tuning/evaluate_loro.sh

# Re-run one fold
FOLDS=Sympy LORO_RUNS_ROOT=/scratch/loro fine-tuning/evaluate_loro.sh
```

Output structure:

```
fine-tuning/evaluations/llm/vllm/<alias>/<repo>/<instance>/{answer,traj}.json
```

---

## 5 · Merging an adapter (standalone)

```bash
python fine-tuning/merge.py \
  --adapter-path /scratch/runs/gemma4-r64 \
  --base-model   /path/to/gemma4-4b \
  --output-dir   /scratch/runs/gemma4-r64-merged
```

Runs in bf16, single GPU; no training needed.

---

## Unsloth backend (longer context on H100)

`--use-unsloth` swaps the model-loading and LoRA-application layer from
transformers + bitsandbytes + PEFT to [Unsloth](https://unsloth.ai/docs)'s
`FastModel` API. Unsloth's fused kernels and offloaded ("unsloth") gradient
checkpointing fit a substantially longer context window on the same GPU — the
motivation here is training gemma4-4b at high `--max-seq-length` on an H100.

Everything else is unchanged: the dataset, chat-template / tool-call wire
format, the assistant-turn loss mask, the hyperparameters, and the TRL
`SFTTrainer`. The default path (no flag) behaves exactly as before.

```bash
CUDA_VISIBLE_DEVICES=0 python fine-tuning/train.py \
  --model /path/to/gemma4-4b \
  --output-dir /scratch/runs/gemma4-r64-unsloth \
  --use-unsloth \
  --batch-size 1 --grad-accum 32 \
  --max-seq-length 32768 \
  --epochs 2 --logging-steps 1
```

Unsloth is pinned in `environment.yml` (`unsloth==2026.5.8`). This release caps
`transformers<=5.5.0` and needs `trl>=0.18.2` / `bitsandbytes>=0.45.5`, which is
why those pins are set as they are. To add it to an existing env:

```bash
pip install unsloth==2026.5.8
```

Notes:

- `FORCE_ATTN_IMPL` does not apply — Unsloth selects its own attention kernels.
- The resulting adapter is a standard PEFT adapter, so `merge.py` /
  `--merge-after-training` work unchanged.
- LoRA is scoped to the language tower via `finetune_vision_layers=False`
  (the equivalent of the default path's `language_model.*` regex).
- The `num_kv_shared_layers=0` vLLM-compatibility override is forwarded to
  `FastModel.from_pretrained`; if your Unsloth build rejects the `config`
  kwarg, training logs a loud warning — verify serving coherence before
  trusting that run.
- Other models (e.g. Qwen) train through the same flag with no special-casing.

## Known footguns (Gemma 4 4B specifically)

1. **Some layers have `head_dim=512`.** Gemma 4 4B alternates head_dim 256 /
   512 across decoder layers. Flash Attention 2 (any version through 2.8.x)
   caps at `head_dim <= 256`, so FA2 crashes on the 512 layers. Same for
   PyTorch SDPA's flash / mem_efficient / cuDNN backends. **Use
   `FORCE_ATTN_IMPL=sdpa`** — SDPA falls through to the math kernel for those
   layers. At L=8192 this fits; at L=16384 you'll OOM during backward; L=32768
   is unreachable on the current stack.

2. **LoRA target modules must be a regex scoped to `language_model.*`.** Gemma
   4 is multimodal; its vision tower wraps projections in
   `Gemma4ClippableLinear` while the language model has plain `Linear4bit`.
   The previous suffix-match `q_proj.linear` matched only the vision tower —
   LoRA was attached there and never participated in text-only forward,
   producing flat loss and zero grad_norm. The default for Gemma 4 4B is now:

   ```
   r".*language_model\..*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)$"
   ```

   See [`finetune/config.py`](finetune/config.py).

3. **Chat-turn boundaries are discovered at runtime.** Literal `<start_of_turn>`
   does not exist in Gemma 4's vocab as a single token — the chat template
   emits special tokens `105` (`<|turn>`) and `106` (`<turn|>`). The collator
   probes the tokenizer at startup to find the real boundary IDs. See
   `_discover_chat_boundaries` in [`finetune/trainer.py`](finetune/trainer.py).

4. **Multi-GPU FSDP-QLoRA does not work on this stack** (accelerate 1.x + bnb +
   PEFT + paged_adamw_8bit silently zero-grads, plus the sharded save doesn't
   produce PEFT-format adapter files). `fsdp_qlora.yaml` is left in the repo
   for reference, but single-GPU is the working path until DeepSpeed ZeRO-3 or
   FSDP-2 + bnb compatibility lands.

---

## SLURM example

```bash
#!/usr/bin/env bash
#SBATCH --job-name=gemma4-loro
#SBATCH --gres=gpu:h100:1
#SBATCH --mem=80G
#SBATCH --cpus-per-task=8
#SBATCH --time=06:00:00
#SBATCH --output=logs/%j.out

module load StdEnv/2023
conda activate RepoBehave_finetune

FORCE_ATTN_IMPL=sdpa CUDA_VISIBLE_DEVICES=0 python fine-tuning/train_loro.py \
  --model /home/hamedth/projects/def-hemmati-ac/hamedth/hugging_face/gemma4-4b \
  --output-root "$SCRATCH/loro-$SLURM_JOB_ID" \
  --max-seq-length 8192 --epochs 2 \
  --merge-after-training
```
