## First-Time Project Setup

Run this first:

```bash
conda create -n repo python=3.11
conda activate repo
pip install -r requirements.txt
```

## Evaluation Scripts

All evaluation runner and scoring docs were moved to:
- [evaluation_scripts/README.md](evaluation_scripts/README.md)

Start there for:
- LLM + RepoMap host evaluation
- Cursor/Claude/SWE-Agent Docker evaluations
- Scoring with `evaluate_qa_answers.py`
