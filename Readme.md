## First-Time Project Setup

### Option A — pip (minimal)

Run this first:

```bash
conda create -n repo python=3.11
conda activate repo
pip install -r requirements.txt
```

### Option B — conda (full repo vs fine-tuning)

- **General work + `evaluation_scripts/` (OpenAI/Gemini/Anthropic clients, vLLM, etc.)**:
  - `environment.yml` → environment name `Triad_env`
- **QLoRA fine-tuning only** (`fine-tuning/train.py`):
  - `fine-tuning/environment.yml` → environment name `Triad_finetune`

```bash
conda env update -f environment.yml --prune
# or, for training only:
conda env update -f fine-tuning/environment.yml --prune
```

## Evaluation Scripts

All evaluation runner and scoring docs were moved to:
- [evaluation_scripts/README.md](evaluation_scripts/README.md)

Start there for:
- LLM + RepoMap host evaluation
- Cursor/Claude/SWE-Agent Docker evaluations
- Scoring with `evaluate_qa_answers.py`
