## Project Setup

## Setup these 2 environments separately for evaluation:

### 1
```bash
conda create -n repo python=3.11
conda activate repo
pip install -r requirements.txt
conda deactivate
```

### 2

```bash
conda env create -f environment.yml
```

## Evaluation Scripts

All evaluation runner and scoring docs were moved to:
- [evaluation_scripts/README.md](evaluation_scripts/README.md)

Start there for:
- LLM evaluation
- Cursor/Claude/SWE-Agent evaluations
- Scoring with `evaluate_qa_answers.py`


## Citation & License

This project is licensed under the MIT License. See [LICENSE.md](LICENSE.md).

This project references SWE-bench Live benchmark resources and Docker images.
Those third-party resources are not relicensed by this repository; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for attribution and license
notes.
