## Results (faker_qa + Keras, combined)

Per model-tool, per question-kind success rate on the combined `faker_qa` and `Keras`
instances.

| tool | vendor | model | question kind | total | success rate |
|---|---|---|---|---|---|
| cursor |  | gpt-5.3-codex | C1_IntraProceduralCFG | 3 | 100 |
| cursor |  | gpt-5.3-codex | C2_InterProceduralCFG | 20 | 75 |
| cursor |  | gpt-5.3-codex | C3_Loops | 2 | 100 |
| cursor |  | gpt-5.3-codex | C4_ProgramState | 20 | 95 |
| cursor |  | gpt-5.3-codex | C5_DataFlow | 10 | 100 |
| cursor |  | gpt-5.3-codex | C6_Exceptions | 8 | 100 |
| cursor |  | gpt-5.3-codex | M1_IntraProceduralCFG | 2 | 50 |
| cursor |  | gpt-5.3-codex | M4_ProgramState | 4 | 25 |
| cursor |  | gpt-5.3-codex | M7_Invariants | 10 | 100 |
| cursor |  | gpt-5.3-codex-high | C1_IntraProceduralCFG | 3 | 100 |
| cursor |  | gpt-5.3-codex-high | C2_InterProceduralCFG | 14 | 57.14 |
| cursor |  | gpt-5.3-codex-high | C4_ProgramState | 9 | 100 |
| cursor |  | gpt-5.3-codex-high | C6_Exceptions | 2 | 100 |
| cursor |  | gpt-5.3-codex-high | M1_IntraProceduralCFG | 1 | 100 |
| cursor |  | gpt-5.3-codex-high | M4_ProgramState | 3 | 66.67 |
| cursor |  | gpt-5.3-codex-high | M7_Invariants | 8 | 100 |
| llm | fireworks | gpt-oss-20b | C1_IntraProceduralCFG | 3 | 66.67 |
| llm | fireworks | gpt-oss-20b | C2_InterProceduralCFG | 20 | 20 |
| llm | fireworks | gpt-oss-20b | C3_Loops | 2 | 0 |
| llm | fireworks | gpt-oss-20b | C4_ProgramState | 20 | 5 |
| llm | fireworks | gpt-oss-20b | C5_DataFlow | 10 | 0 |
| llm | fireworks | gpt-oss-20b | C6_Exceptions | 8 | 50 |
| llm | fireworks | gpt-oss-20b | M1_IntraProceduralCFG | 2 | 50 |
| llm | fireworks | gpt-oss-20b | M4_ProgramState | 4 | 25 |
| llm | fireworks | gpt-oss-20b | M7_Invariants | 10 | 80 |
| llm | gemini | gemini-3.5-flash | C1_IntraProceduralCFG | 3 | 100 |
| llm | gemini | gemini-3.5-flash | C2_InterProceduralCFG | 20 | 45 |
| llm | gemini | gemini-3.5-flash | C3_Loops | 2 | 0 |
| llm | gemini | gemini-3.5-flash | C4_ProgramState | 20 | 50 |
| llm | gemini | gemini-3.5-flash | C5_DataFlow | 10 | 50 |
| llm | gemini | gemini-3.5-flash | C6_Exceptions | 8 | 37.5 |
| llm | gemini | gemini-3.5-flash | M1_IntraProceduralCFG | 2 | 50 |
| llm | gemini | gemini-3.5-flash | M4_ProgramState | 4 | 50 |
| llm | gemini | gemini-3.5-flash | M7_Invariants | 10 | 100 |
| llm | openai | gpt-5.3-codex | C1_IntraProceduralCFG | 3 | 100 |
| llm | openai | gpt-5.3-codex | C2_InterProceduralCFG | 20 | 45 |
| llm | openai | gpt-5.3-codex | C3_Loops | 2 | 0 |
| llm | openai | gpt-5.3-codex | C4_ProgramState | 20 | 10 |
| llm | openai | gpt-5.3-codex | C5_DataFlow | 10 | 0 |
| llm | openai | gpt-5.3-codex | C6_Exceptions | 8 | 62.5 |
| llm | openai | gpt-5.3-codex | M1_IntraProceduralCFG | 2 | 50 |
| llm | openai | gpt-5.3-codex | M4_ProgramState | 4 | 25 |
| llm | openai | gpt-5.3-codex | M7_Invariants | 10 | 100 |
| llm | openai | gpt-5.4-2026-03-05 | C1_IntraProceduralCFG | 3 | 66.67 |
| llm | openai | gpt-5.4-2026-03-05 | C2_InterProceduralCFG | 20 | 35 |
| llm | openai | gpt-5.4-2026-03-05 | C3_Loops | 2 | 0 |
| llm | openai | gpt-5.4-2026-03-05 | C4_ProgramState | 20 | 35 |
| llm | openai | gpt-5.4-2026-03-05 | C5_DataFlow | 10 | 0 |
| llm | openai | gpt-5.4-2026-03-05 | C6_Exceptions | 8 | 75 |
| llm | openai | gpt-5.4-2026-03-05 | M1_IntraProceduralCFG | 2 | 50 |
| llm | openai | gpt-5.4-2026-03-05 | M4_ProgramState | 4 | 25 |
| llm | openai | gpt-5.4-2026-03-05 | M7_Invariants | 10 | 100 |
| llm | vllm | gemm4-31b | C1_IntraProceduralCFG | 3 | 100 |
| llm | vllm | gemm4-31b | C2_InterProceduralCFG | 20 | 20 |
| llm | vllm | gemm4-31b | C3_Loops | 2 | 0 |
| llm | vllm | gemm4-31b | C4_ProgramState | 20 | 10 |
| llm | vllm | gemm4-31b | C5_DataFlow | 10 | 0 |
| llm | vllm | gemm4-31b | C6_Exceptions | 8 | 37.5 |
| llm | vllm | gemm4-31b | M1_IntraProceduralCFG | 2 | 50 |
| llm | vllm | gemm4-31b | M4_ProgramState | 4 | 25 |
| llm | vllm | gemm4-31b | M7_Invariants | 10 | 60 |
| llm | vllm | gemma4-4b | C1_IntraProceduralCFG | 3 | 66.67 |
| llm | vllm | gemma4-4b | C2_InterProceduralCFG | 20 | 20 |
| llm | vllm | gemma4-4b | C3_Loops | 2 | 0 |
| llm | vllm | gemma4-4b | C4_ProgramState | 20 | 5 |
| llm | vllm | gemma4-4b | C5_DataFlow | 10 | 0 |
| llm | vllm | gemma4-4b | C6_Exceptions | 8 | 0 |
| llm | vllm | gemma4-4b | M1_IntraProceduralCFG | 2 | 50 |
| llm | vllm | gemma4-4b | M4_ProgramState | 4 | 25 |
| llm | vllm | gemma4-4b | M7_Invariants | 10 | 60 |