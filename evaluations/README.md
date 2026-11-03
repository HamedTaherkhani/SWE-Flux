# Evaluations

Results of every evaluated system on the 480 RepoBehave instances (12 repositories, 13 question kinds). Answers are scored by `evaluation_scripts/evaluate_qa_answers.py` against the execution-derived oracle of each instance, with a tolerant comparator (numeric tolerance, accepted alternative qualified names). A missing or unparsable answer counts as wrong.

Folder layout: `evaluations/<tool>/<model>/<repo>/<instance>/{answer.json, traj.json, ...}`, where `<tool>` is `llm/<vendor>` for the RepoBehave LLM harness (read-only repository tools, no execution), `codex-noexec` and `claude_code-noexec` for agents with repository read access and no execution, and `cursor` for agents with full execution. The tables below cover the five harness LLMs and the three no-execution agents.

Regenerate all tables with:

```bash
python3 analysis/difficulty_split.py --weights "lines_covered=0.7,max_stack_depth=0.3"   # buckets -> analysis/difficulty_split.csv
python3 analysis/difficulty_tables.py                                                     # markdown for this file
```

## Results

### Accuracy per repository

Accuracy in % over all instances of each repository (n in the second column). LLMs run in the RepoBehave harness with read-only repository tools; agents run without execution (repository read access only).

| Repository | n | GPT-5.4 | GPT-5.3-Codex | GPT-OSS-20B | Gemma-4-4B | Gemma-4-31B | Codex (GPT-5.4) | Codex (GPT-6-Sol) | Claude Code (Opus 5.5) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cfnlint_qa | 40 | 65.0 | 60.0 | 35.0 | 30.0 | 27.5 | 72.5 | 75.0 | 72.5 |
| faker_qa | 39 | 38.5 | 35.9 | 28.2 | 20.5 | 20.5 | 51.3 | 53.8 | 56.4 |
| Keras | 40 | 62.5 | 47.5 | 30.0 | 27.5 | 32.5 | 70.0 | 77.5 | 65.0 |
| matplotlib_qa | 40 | 35.0 | 32.5 | 25.0 | 32.5 | 20.0 | 65.0 | 75.0 | 67.5 |
| pybamm_qa | 40 | 12.5 | 7.5 | 5.0 | 0.0 | 5.0 | 57.5 | 62.5 | 67.5 |
| pydata_xarray | 40 | 50.0 | 45.0 | 25.0 | 10.0 | 32.5 | 75.0 | 67.5 | 65.0 |
| python-control | 41 | 17.1 | 17.1 | 4.9 | 14.6 | 2.4 | 53.7 | 63.4 | 78.0 |
| qtile | 40 | 15.0 | 20.0 | 7.5 | 0.0 | 2.5 | 45.0 | 67.5 | 60.0 |
| reflex_qa | 41 | 29.3 | 24.4 | 17.1 | 19.5 | 7.3 | 46.3 | 53.7 | 53.7 |
| Sympy | 39 | 25.6 | 23.1 | 12.8 | 12.8 | 20.5 | 53.8 | 66.7 | 56.4 |
| Telegram_bot | 40 | 52.5 | 47.5 | 30.0 | 12.5 | 22.5 | 87.5 | 80.0 | 82.5 |
| yt_dlp | 40 | 50.0 | 45.0 | 27.5 | 27.5 | 37.5 | 90.0 | 90.0 | 95.0 |
| **All** | 480 | **37.7** | **33.8** | **20.6** | **17.3** | **19.2** | **64.0** | **69.4** | **68.3** |

### Accuracy per question kind

| Kind | n | GPT-5.4 | GPT-5.3-Codex | GPT-OSS-20B | Gemma-4-4B | Gemma-4-31B | Codex (GPT-5.4) | Codex (GPT-6-Sol) | Claude Code (Opus 5.5) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S1_IntraProceduralCFG | 23 | 69.6 | 65.2 | 47.8 | 43.5 | 43.5 | 65.2 | 82.6 | 73.9 |
| S2_Loops | 14 | 28.6 | 28.6 | 21.4 | 28.6 | 42.9 | 85.7 | 78.6 | 71.4 |
| S3_ProgramState | 106 | 48.1 | 36.8 | 13.2 | 14.2 | 15.1 | 79.2 | 83.0 | 80.2 |
| S4_DataFlow | 59 | 6.8 | 0.0 | 1.7 | 0.0 | 0.0 | 30.5 | 44.1 | 42.4 |
| S5_Exceptions | 28 | 64.3 | 64.3 | 35.7 | 7.1 | 39.3 | 71.4 | 78.6 | 78.6 |
| S6_InterProceduralCFG | 78 | 25.6 | 24.4 | 11.5 | 9.0 | 11.5 | 52.6 | 60.3 | 51.3 |
| M1_IntraProceduralCFG | 25 | 28.0 | 32.0 | 20.0 | 12.0 | 20.0 | 48.0 | 40.0 | 40.0 |
| M2_Loops | 13 | 53.8 | 46.2 | 38.5 | 30.8 | 38.5 | 69.2 | 69.2 | 69.2 |
| M3_ProgramState | 28 | 42.9 | 39.3 | 35.7 | 28.6 | 21.4 | 82.1 | 82.1 | 78.6 |
| M4_DataFlow | 33 | 0.0 | 6.1 | 3.0 | 0.0 | 0.0 | 63.6 | 69.7 | 78.8 |
| M5_ExceptionalBehavior | 11 | 45.5 | 27.3 | 18.2 | 0.0 | 18.2 | 72.7 | 63.6 | 72.7 |
| M6_InterProceduralCFG | 20 | 15.0 | 15.0 | 0.0 | 10.0 | 0.0 | 25.0 | 45.0 | 70.0 |
| M7_Invariants | 42 | 81.0 | 81.0 | 66.7 | 66.7 | 52.4 | 92.9 | 92.9 | 95.2 |

### Accuracy by difficulty

Instances are split into easy / medium / hard terciles (160 each) by a weighted composite of two runtime metrics harvested while the instance's test executes: **lines covered** (distinct repository lines executed, weight 0.7) and **max stack depth** (deepest in-repository call stack, weight 0.3). Each instance's percentile rank on each metric is combined with those weights; the weights were chosen by `analysis/difficulty_weight_search.py` to maximise the easy-to-hard accuracy gap while keeping every system monotone. Bucket medians: easy 35 lines / depth 3, medium 192 / 8, hard 785 / 18. Produced by `analysis/difficulty_split.py` and `analysis/difficulty_tables.py`. Agents run without execution (repository read access only). Cells are accuracy in %; the n column gives the number of easy / medium / hard instances in the row.

#### Overall

| System | Easy | Medium | Hard | All |
|---|---:|---:|---:|---:|
| GPT-5.4 | 45.0 | 35.0 | 33.1 | 37.7 |
| GPT-5.3-Codex | 45.6 | 29.4 | 26.2 | 33.8 |
| GPT-OSS-20B | 27.5 | 18.1 | 16.2 | 20.6 |
| Gemma-4-4B | 22.5 | 15.6 | 13.8 | 17.3 |
| Gemma-4-31B | 24.4 | 16.9 | 16.2 | 19.2 |
| Codex (GPT-5.4) | 70.6 | 68.8 | 52.5 | 64.0 |
| Codex (GPT-6-Sol) | 78.1 | 71.9 | 58.1 | 69.4 |
| Claude Code (Opus 5.5) | 77.5 | 69.4 | 58.1 | 68.3 |

#### By question kind

**GPT-5.4**

| Kind | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| S1_IntraProceduralCFG | 9/8/6 | 55.6 | 75.0 | 83.3 | 69.6 |
| S2_Loops | 7/5/2 | 28.6 | 20.0 | 50.0 | 28.6 |
| S3_ProgramState | 29/37/40 | 65.5 | 43.2 | 40.0 | 48.1 |
| S4_DataFlow | 30/16/13 | 10.0 | 6.2 | 0.0 | 6.8 |
| S5_Exceptions | 13/8/7 | 76.9 | 50.0 | 57.1 | 64.3 |
| S6_InterProceduralCFG | 14/24/40 | 42.9 | 20.8 | 22.5 | 25.6 |
| M1_IntraProceduralCFG | 11/9/5 | 36.4 | 33.3 | 0.0 | 28.0 |
| M2_Loops | 6/6/1 | 50.0 | 66.7 | 0.0 | 53.8 |
| M3_ProgramState | 11/12/5 | 63.6 | 33.3 | 20.0 | 42.9 |
| M4_DataFlow | 9/20/4 | 0.0 | 0.0 | 0.0 | 0.0 |
| M5_ExceptionalBehavior | 0/2/9 | - | 50.0 | 44.4 | 45.5 |
| M6_InterProceduralCFG | 1/3/16 | 0.0 | 33.3 | 12.5 | 15.0 |
| M7_Invariants | 20/10/12 | 65.0 | 100.0 | 91.7 | 81.0 |

**GPT-5.3-Codex**

| Kind | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| S1_IntraProceduralCFG | 9/8/6 | 55.6 | 62.5 | 83.3 | 65.2 |
| S2_Loops | 7/5/2 | 28.6 | 20.0 | 50.0 | 28.6 |
| S3_ProgramState | 29/37/40 | 62.1 | 29.7 | 25.0 | 36.8 |
| S4_DataFlow | 30/16/13 | 0.0 | 0.0 | 0.0 | 0.0 |
| S5_Exceptions | 13/8/7 | 92.3 | 37.5 | 42.9 | 64.3 |
| S6_InterProceduralCFG | 14/24/40 | 42.9 | 20.8 | 20.0 | 24.4 |
| M1_IntraProceduralCFG | 11/9/5 | 54.5 | 22.2 | 0.0 | 32.0 |
| M2_Loops | 6/6/1 | 50.0 | 50.0 | 0.0 | 46.2 |
| M3_ProgramState | 11/12/5 | 63.6 | 33.3 | 0.0 | 39.3 |
| M4_DataFlow | 9/20/4 | 11.1 | 5.0 | 0.0 | 6.1 |
| M5_ExceptionalBehavior | 0/2/9 | - | 50.0 | 22.2 | 27.3 |
| M6_InterProceduralCFG | 1/3/16 | 0.0 | 33.3 | 12.5 | 15.0 |
| M7_Invariants | 20/10/12 | 65.0 | 100.0 | 91.7 | 81.0 |

**GPT-OSS-20B**

| Kind | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| S1_IntraProceduralCFG | 9/8/6 | 33.3 | 37.5 | 83.3 | 47.8 |
| S2_Loops | 7/5/2 | 42.9 | 0.0 | 0.0 | 21.4 |
| S3_ProgramState | 29/37/40 | 13.8 | 13.5 | 12.5 | 13.2 |
| S4_DataFlow | 30/16/13 | 3.3 | 0.0 | 0.0 | 1.7 |
| S5_Exceptions | 13/8/7 | 30.8 | 37.5 | 42.9 | 35.7 |
| S6_InterProceduralCFG | 14/24/40 | 14.3 | 16.7 | 7.5 | 11.5 |
| M1_IntraProceduralCFG | 11/9/5 | 27.3 | 22.2 | 0.0 | 20.0 |
| M2_Loops | 6/6/1 | 50.0 | 33.3 | 0.0 | 38.5 |
| M3_ProgramState | 11/12/5 | 63.6 | 25.0 | 0.0 | 35.7 |
| M4_DataFlow | 9/20/4 | 0.0 | 5.0 | 0.0 | 3.0 |
| M5_ExceptionalBehavior | 0/2/9 | - | 0.0 | 22.2 | 18.2 |
| M6_InterProceduralCFG | 1/3/16 | 0.0 | 0.0 | 0.0 | 0.0 |
| M7_Invariants | 20/10/12 | 70.0 | 60.0 | 66.7 | 66.7 |

**Gemma-4-4B**

| Kind | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| S1_IntraProceduralCFG | 9/8/6 | 33.3 | 37.5 | 66.7 | 43.5 |
| S2_Loops | 7/5/2 | 57.1 | 0.0 | 0.0 | 28.6 |
| S3_ProgramState | 29/37/40 | 24.1 | 8.1 | 12.5 | 14.2 |
| S4_DataFlow | 30/16/13 | 0.0 | 0.0 | 0.0 | 0.0 |
| S5_Exceptions | 13/8/7 | 7.7 | 12.5 | 0.0 | 7.1 |
| S6_InterProceduralCFG | 14/24/40 | 7.1 | 8.3 | 10.0 | 9.0 |
| M1_IntraProceduralCFG | 11/9/5 | 9.1 | 22.2 | 0.0 | 12.0 |
| M2_Loops | 6/6/1 | 33.3 | 33.3 | 0.0 | 30.8 |
| M3_ProgramState | 11/12/5 | 36.4 | 33.3 | 0.0 | 28.6 |
| M4_DataFlow | 9/20/4 | 0.0 | 0.0 | 0.0 | 0.0 |
| M5_ExceptionalBehavior | 0/2/9 | - | 0.0 | 0.0 | 0.0 |
| M6_InterProceduralCFG | 1/3/16 | 0.0 | 33.3 | 6.2 | 10.0 |
| M7_Invariants | 20/10/12 | 65.0 | 70.0 | 66.7 | 66.7 |

**Gemma-4-31B**

| Kind | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| S1_IntraProceduralCFG | 9/8/6 | 33.3 | 37.5 | 66.7 | 43.5 |
| S2_Loops | 7/5/2 | 57.1 | 20.0 | 50.0 | 42.9 |
| S3_ProgramState | 29/37/40 | 20.7 | 8.1 | 17.5 | 15.1 |
| S4_DataFlow | 30/16/13 | 0.0 | 0.0 | 0.0 | 0.0 |
| S5_Exceptions | 13/8/7 | 46.2 | 12.5 | 57.1 | 39.3 |
| S6_InterProceduralCFG | 14/24/40 | 14.3 | 16.7 | 7.5 | 11.5 |
| M1_IntraProceduralCFG | 11/9/5 | 36.4 | 11.1 | 0.0 | 20.0 |
| M2_Loops | 6/6/1 | 33.3 | 50.0 | 0.0 | 38.5 |
| M3_ProgramState | 11/12/5 | 36.4 | 16.7 | 0.0 | 21.4 |
| M4_DataFlow | 9/20/4 | 0.0 | 0.0 | 0.0 | 0.0 |
| M5_ExceptionalBehavior | 0/2/9 | - | 50.0 | 11.1 | 18.2 |
| M6_InterProceduralCFG | 1/3/16 | 0.0 | 0.0 | 0.0 | 0.0 |
| M7_Invariants | 20/10/12 | 40.0 | 80.0 | 50.0 | 52.4 |

**Codex (GPT-5.4)**

| Kind | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| S1_IntraProceduralCFG | 9/8/6 | 55.6 | 62.5 | 83.3 | 65.2 |
| S2_Loops | 7/5/2 | 85.7 | 80.0 | 100.0 | 85.7 |
| S3_ProgramState | 29/37/40 | 100.0 | 81.1 | 62.5 | 79.2 |
| S4_DataFlow | 30/16/13 | 36.7 | 37.5 | 7.7 | 30.5 |
| S5_Exceptions | 13/8/7 | 76.9 | 62.5 | 71.4 | 71.4 |
| S6_InterProceduralCFG | 14/24/40 | 64.3 | 58.3 | 45.0 | 52.6 |
| M1_IntraProceduralCFG | 11/9/5 | 45.5 | 77.8 | 0.0 | 48.0 |
| M2_Loops | 6/6/1 | 66.7 | 66.7 | 100.0 | 69.2 |
| M3_ProgramState | 11/12/5 | 81.8 | 91.7 | 60.0 | 82.1 |
| M4_DataFlow | 9/20/4 | 77.8 | 55.0 | 75.0 | 63.6 |
| M5_ExceptionalBehavior | 0/2/9 | - | 100.0 | 66.7 | 72.7 |
| M6_InterProceduralCFG | 1/3/16 | 100.0 | 33.3 | 18.8 | 25.0 |
| M7_Invariants | 20/10/12 | 85.0 | 100.0 | 100.0 | 92.9 |

**Codex (GPT-6-Sol)**

| Kind | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| S1_IntraProceduralCFG | 9/8/6 | 77.8 | 87.5 | 83.3 | 82.6 |
| S2_Loops | 7/5/2 | 71.4 | 80.0 | 100.0 | 78.6 |
| S3_ProgramState | 29/37/40 | 100.0 | 75.7 | 77.5 | 83.0 |
| S4_DataFlow | 30/16/13 | 60.0 | 43.8 | 7.7 | 44.1 |
| S5_Exceptions | 13/8/7 | 92.3 | 62.5 | 71.4 | 78.6 |
| S6_InterProceduralCFG | 14/24/40 | 85.7 | 62.5 | 50.0 | 60.3 |
| M1_IntraProceduralCFG | 11/9/5 | 36.4 | 66.7 | 0.0 | 40.0 |
| M2_Loops | 6/6/1 | 66.7 | 66.7 | 100.0 | 69.2 |
| M3_ProgramState | 11/12/5 | 90.9 | 100.0 | 20.0 | 82.1 |
| M4_DataFlow | 9/20/4 | 66.7 | 65.0 | 100.0 | 69.7 |
| M5_ExceptionalBehavior | 0/2/9 | - | 100.0 | 55.6 | 63.6 |
| M6_InterProceduralCFG | 1/3/16 | 100.0 | 66.7 | 37.5 | 45.0 |
| M7_Invariants | 20/10/12 | 85.0 | 100.0 | 100.0 | 92.9 |

**Claude Code (Opus 5.5)**

| Kind | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| S1_IntraProceduralCFG | 9/8/6 | 77.8 | 62.5 | 83.3 | 73.9 |
| S2_Loops | 7/5/2 | 71.4 | 60.0 | 100.0 | 71.4 |
| S3_ProgramState | 29/37/40 | 100.0 | 75.7 | 70.0 | 80.2 |
| S4_DataFlow | 30/16/13 | 53.3 | 50.0 | 7.7 | 42.4 |
| S5_Exceptions | 13/8/7 | 84.6 | 62.5 | 85.7 | 78.6 |
| S6_InterProceduralCFG | 14/24/40 | 85.7 | 54.2 | 37.5 | 51.3 |
| M1_IntraProceduralCFG | 11/9/5 | 45.5 | 44.4 | 20.0 | 40.0 |
| M2_Loops | 6/6/1 | 66.7 | 66.7 | 100.0 | 69.2 |
| M3_ProgramState | 11/12/5 | 81.8 | 91.7 | 40.0 | 78.6 |
| M4_DataFlow | 9/20/4 | 77.8 | 75.0 | 100.0 | 78.8 |
| M5_ExceptionalBehavior | 0/2/9 | - | 100.0 | 66.7 | 72.7 |
| M6_InterProceduralCFG | 1/3/16 | 100.0 | 100.0 | 62.5 | 70.0 |
| M7_Invariants | 20/10/12 | 90.0 | 100.0 | 100.0 | 95.2 |

#### By repository

**GPT-5.4**

| Repository | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| cfnlint_qa | 8/19/13 | 75.0 | 68.4 | 53.8 | 65.0 |
| faker_qa | 10/24/5 | 60.0 | 29.2 | 40.0 | 38.5 |
| Keras | 5/7/28 | 100.0 | 42.9 | 60.7 | 62.5 |
| matplotlib_qa | 24/4/12 | 37.5 | 50.0 | 25.0 | 35.0 |
| pybamm_qa | 2/16/22 | 0.0 | 6.2 | 18.2 | 12.5 |
| pydata_xarray | 15/8/17 | 66.7 | 37.5 | 41.2 | 50.0 |
| python-control | 12/19/10 | 8.3 | 21.1 | 20.0 | 17.1 |
| qtile | 31/9/0 | 19.4 | 0.0 | - | 15.0 |
| reflex_qa | 8/16/17 | 50.0 | 43.8 | 5.9 | 29.3 |
| Sympy | 1/6/32 | 0.0 | 33.3 | 25.0 | 25.6 |
| Telegram_bot | 11/25/4 | 81.8 | 40.0 | 50.0 | 52.5 |
| yt_dlp | 33/7/0 | 48.5 | 57.1 | - | 50.0 |

**GPT-5.3-Codex**

| Repository | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| cfnlint_qa | 8/19/13 | 75.0 | 68.4 | 38.5 | 60.0 |
| faker_qa | 10/24/5 | 60.0 | 25.0 | 40.0 | 35.9 |
| Keras | 5/7/28 | 80.0 | 28.6 | 46.4 | 47.5 |
| matplotlib_qa | 24/4/12 | 37.5 | 50.0 | 16.7 | 32.5 |
| pybamm_qa | 2/16/22 | 0.0 | 6.2 | 9.1 | 7.5 |
| pydata_xarray | 15/8/17 | 60.0 | 37.5 | 35.3 | 45.0 |
| python-control | 12/19/10 | 16.7 | 15.8 | 20.0 | 17.1 |
| qtile | 31/9/0 | 25.8 | 0.0 | - | 20.0 |
| reflex_qa | 8/16/17 | 50.0 | 31.2 | 5.9 | 24.4 |
| Sympy | 1/6/32 | 0.0 | 33.3 | 21.9 | 23.1 |
| Telegram_bot | 11/25/4 | 90.9 | 28.0 | 50.0 | 47.5 |
| yt_dlp | 33/7/0 | 45.5 | 42.9 | - | 45.0 |

**GPT-OSS-20B**

| Repository | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| cfnlint_qa | 8/19/13 | 37.5 | 42.1 | 23.1 | 35.0 |
| faker_qa | 10/24/5 | 40.0 | 25.0 | 20.0 | 28.2 |
| Keras | 5/7/28 | 40.0 | 28.6 | 28.6 | 30.0 |
| matplotlib_qa | 24/4/12 | 37.5 | 0.0 | 8.3 | 25.0 |
| pybamm_qa | 2/16/22 | 0.0 | 0.0 | 9.1 | 5.0 |
| pydata_xarray | 15/8/17 | 26.7 | 12.5 | 29.4 | 25.0 |
| python-control | 12/19/10 | 8.3 | 5.3 | 0.0 | 4.9 |
| qtile | 31/9/0 | 9.7 | 0.0 | - | 7.5 |
| reflex_qa | 8/16/17 | 50.0 | 12.5 | 5.9 | 17.1 |
| Sympy | 1/6/32 | 0.0 | 0.0 | 15.6 | 12.8 |
| Telegram_bot | 11/25/4 | 54.5 | 24.0 | 0.0 | 30.0 |
| yt_dlp | 33/7/0 | 24.2 | 42.9 | - | 27.5 |

**Gemma-4-4B**

| Repository | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| cfnlint_qa | 8/19/13 | 37.5 | 31.6 | 23.1 | 30.0 |
| faker_qa | 10/24/5 | 50.0 | 12.5 | 0.0 | 20.5 |
| Keras | 5/7/28 | 40.0 | 14.3 | 28.6 | 27.5 |
| matplotlib_qa | 24/4/12 | 41.7 | 25.0 | 16.7 | 32.5 |
| pybamm_qa | 2/16/22 | 0.0 | 0.0 | 0.0 | 0.0 |
| pydata_xarray | 15/8/17 | 6.7 | 0.0 | 17.6 | 10.0 |
| python-control | 12/19/10 | 0.0 | 26.3 | 10.0 | 14.6 |
| qtile | 31/9/0 | 0.0 | 0.0 | - | 0.0 |
| reflex_qa | 8/16/17 | 50.0 | 18.8 | 5.9 | 19.5 |
| Sympy | 1/6/32 | 0.0 | 16.7 | 12.5 | 12.8 |
| Telegram_bot | 11/25/4 | 27.3 | 8.0 | 0.0 | 12.5 |
| yt_dlp | 33/7/0 | 24.2 | 42.9 | - | 27.5 |

**Gemma-4-31B**

| Repository | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| cfnlint_qa | 8/19/13 | 37.5 | 31.6 | 15.4 | 27.5 |
| faker_qa | 10/24/5 | 30.0 | 20.8 | 0.0 | 20.5 |
| Keras | 5/7/28 | 60.0 | 28.6 | 28.6 | 32.5 |
| matplotlib_qa | 24/4/12 | 25.0 | 0.0 | 16.7 | 20.0 |
| pybamm_qa | 2/16/22 | 0.0 | 6.2 | 4.5 | 5.0 |
| pydata_xarray | 15/8/17 | 46.7 | 12.5 | 29.4 | 32.5 |
| python-control | 12/19/10 | 0.0 | 5.3 | 0.0 | 2.4 |
| qtile | 31/9/0 | 0.0 | 11.1 | - | 2.5 |
| reflex_qa | 8/16/17 | 12.5 | 6.2 | 5.9 | 7.3 |
| Sympy | 1/6/32 | 0.0 | 33.3 | 18.8 | 20.5 |
| Telegram_bot | 11/25/4 | 36.4 | 16.0 | 25.0 | 22.5 |
| yt_dlp | 33/7/0 | 36.4 | 42.9 | - | 37.5 |

**Codex (GPT-5.4)**

| Repository | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| cfnlint_qa | 8/19/13 | 75.0 | 73.7 | 69.2 | 72.5 |
| faker_qa | 10/24/5 | 70.0 | 45.8 | 40.0 | 51.3 |
| Keras | 5/7/28 | 100.0 | 71.4 | 64.3 | 70.0 |
| matplotlib_qa | 24/4/12 | 70.8 | 75.0 | 50.0 | 65.0 |
| pybamm_qa | 2/16/22 | 100.0 | 68.8 | 45.5 | 57.5 |
| pydata_xarray | 15/8/17 | 80.0 | 87.5 | 64.7 | 75.0 |
| python-control | 12/19/10 | 58.3 | 52.6 | 50.0 | 53.7 |
| qtile | 31/9/0 | 32.3 | 88.9 | - | 45.0 |
| reflex_qa | 8/16/17 | 75.0 | 62.5 | 17.6 | 46.3 |
| Sympy | 1/6/32 | 100.0 | 66.7 | 50.0 | 53.8 |
| Telegram_bot | 11/25/4 | 90.9 | 84.0 | 100.0 | 87.5 |
| yt_dlp | 33/7/0 | 90.9 | 85.7 | - | 90.0 |

**Codex (GPT-6-Sol)**

| Repository | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| cfnlint_qa | 8/19/13 | 75.0 | 78.9 | 69.2 | 75.0 |
| faker_qa | 10/24/5 | 60.0 | 50.0 | 60.0 | 53.8 |
| Keras | 5/7/28 | 100.0 | 85.7 | 71.4 | 77.5 |
| matplotlib_qa | 24/4/12 | 87.5 | 75.0 | 50.0 | 75.0 |
| pybamm_qa | 2/16/22 | 50.0 | 81.2 | 50.0 | 62.5 |
| pydata_xarray | 15/8/17 | 80.0 | 62.5 | 58.8 | 67.5 |
| python-control | 12/19/10 | 66.7 | 63.2 | 60.0 | 63.4 |
| qtile | 31/9/0 | 58.1 | 100.0 | - | 67.5 |
| reflex_qa | 8/16/17 | 87.5 | 68.8 | 23.5 | 53.7 |
| Sympy | 1/6/32 | 100.0 | 66.7 | 65.6 | 66.7 |
| Telegram_bot | 11/25/4 | 90.9 | 76.0 | 75.0 | 80.0 |
| yt_dlp | 33/7/0 | 90.9 | 85.7 | - | 90.0 |

**Claude Code (Opus 5.5)**

| Repository | n (E/M/H) | Easy | Medium | Hard | All |
|---|---|---:|---:|---:|---:|
| cfnlint_qa | 8/19/13 | 75.0 | 73.7 | 69.2 | 72.5 |
| faker_qa | 10/24/5 | 70.0 | 54.2 | 40.0 | 56.4 |
| Keras | 5/7/28 | 100.0 | 42.9 | 64.3 | 65.0 |
| matplotlib_qa | 24/4/12 | 79.2 | 75.0 | 41.7 | 67.5 |
| pybamm_qa | 2/16/22 | 50.0 | 81.2 | 59.1 | 67.5 |
| pydata_xarray | 15/8/17 | 80.0 | 50.0 | 58.8 | 65.0 |
| python-control | 12/19/10 | 66.7 | 73.7 | 100.0 | 78.0 |
| qtile | 31/9/0 | 51.6 | 88.9 | - | 60.0 |
| reflex_qa | 8/16/17 | 87.5 | 62.5 | 29.4 | 53.7 |
| Sympy | 1/6/32 | 100.0 | 50.0 | 56.2 | 56.4 |
| Telegram_bot | 11/25/4 | 90.9 | 80.0 | 75.0 | 82.5 |
| yt_dlp | 33/7/0 | 97.0 | 85.7 | - | 95.0 |
