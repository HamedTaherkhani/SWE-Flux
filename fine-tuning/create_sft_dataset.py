#!/usr/bin/env python3
"""
create_sft_dataset.py

Generate a supervised fine-tuning (SFT) dataset from QA instances across
one or more repositories.

Design:
  - A teacher LLM (default: gpt-5.4) has the oracle answer in its SYSTEM PROMPT
    only — this guides which code to read but is never echoed into the saved
    training conversation.
  - Execution traces are in the user message (training data). The model uses
    them privately to know which code path was taken and what values exist,
    but must reason entirely from source code — never citing the trace.
  - Saved training messages use a student system prompt (oracle-free) so the
    format matches the evaluation setting.
  - Only read_file and list_dir are available; get_repo_map is excluded.
  - The repository is copied from the Docker image and cached locally so
    ReadOnlyRepoTools has accurate file paths.
  - Multiple instances are processed in parallel via ThreadPoolExecutor.
  - API key: --api-key > OPENAI_API_KEY env var > openai_api_key in .env.

Usage:
  python create_sft_dataset.py                        # all repos
  python create_sft_dataset.py --repo Sympy           # one repo
  python create_sft_dataset.py --repo Sympy,faker_qa  # several repos (comma-separated)
  python create_sft_dataset.py --repo Sympy faker_qa  # several repos (multiple args)
  python create_sft_dataset.py --repo Sympy --instances core_expand_mul_indirect_output
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openai

# ---------------------------------------------------------------------------
# Bootstrap: make evaluation_scripts importable
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent  # RepoBehave/
_EVAL_LIB = _REPO_ROOT / "evaluation_scripts" / "llm_eval"
if str(_EVAL_LIB) not in sys.path:
    sys.path.insert(0, str(_EVAL_LIB))

from repo_tools import (  # noqa: E402
    TOOL_DESCRIPTIONS,
    TOOL_INPUT_SCHEMAS,
    INSTANCE_PREVIEW_LIMIT,
    ReadOnlyRepoTools,
    shrink_tool_payload_for_llm,
)
from provider_runner import (  # noqa: E402
    TOOL_PHASE_DONE_SENTINEL,
    TOOL_PHASE_REMINDER_PROMPT,
    FINAL_JSON_PROMPT,
)
from container_runtime import build_container_runtime  # noqa: E402
from run_llm_repomap_eval_host import infer_repo_subdir_for_image  # noqa: E402

# ---------------------------------------------------------------------------
# Top-level paths
# ---------------------------------------------------------------------------
QA_INSTANCES_ROOT = _REPO_ROOT / "qa_instances"
SFT_RECORDS_ROOT = _SCRIPT_DIR / "sft_dataset"
REPO_CACHE_ROOT = _SCRIPT_DIR / "sft_dataset" / "repo_cache"
REPOSITORIES_JSON = _REPO_ROOT / "Repositories.json"

MAX_TRACE_BYTES = 1 * 1024 * 1024  # 1 MB
MAX_READ_LINES = 200
MAX_TOOL_ROUNDS = 30
DEFAULT_MODEL = "gpt-5.4"
DEFAULT_WORKERS = 4

_SKIP_DIRS = {"shared", "qa_artifacts"}

# ---------------------------------------------------------------------------
# Tool definitions — read_file + list_dir only (no get_repo_map)
# ---------------------------------------------------------------------------
TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": TOOL_DESCRIPTIONS[name],
            "parameters": TOOL_INPUT_SCHEMAS[name],
        },
    }
    for name in ("list_dir", "read_file")
]

# ---------------------------------------------------------------------------
# Per-repo configuration
# ---------------------------------------------------------------------------

@dataclass
class RepoConfig:
    name: str
    docker_image: str
    qa_dir: Path            # qa_instances/<name>/
    artifacts_dir: Path     # qa_instances/<name>/qa_artifacts/
    sft_dir: Path           # sft_dataset/<name>/
    cache_dir: Path         # sft_dataset/repo_cache/<name>/
    cache_ready: Path       # sft_dataset/repo_cache/<name>/.ready
    testbed_subdir: str     # e.g. "sympy", "faker", "keras"
    repo_root: Optional[Path] = field(default=None, init=False)


def _load_repos_json() -> Dict[str, str]:
    if not REPOSITORIES_JSON.exists():
        return {}
    return json.loads(REPOSITORIES_JSON.read_text(encoding="utf-8"))


# Subdirectory names that are internal to a repo, not the repo root itself.
# If a question mentions /testbed/lib/, the actual repo is one level higher.
_INTERNAL_SUBDIRS = {
    "lib", "src", "bin", "include", "share", "build", "dist",
    "site-packages", "tests", "test", "docs", "examples",
}


def _infer_testbed_subdir_from_question(qa_dir: Path) -> Optional[str]:
    """Scan oracle.json questions for /testbed/<subdir>/ where subdir is a repo root."""
    for oracle_file in sorted(qa_dir.glob("*/oracle.json")):
        try:
            oracle = json.loads(oracle_file.read_text(encoding="utf-8"))
            question = oracle.get("question", "")
            m = re.search(r"/testbed/([A-Za-z0-9_.\-]+)/", question)
            if m:
                subdir = m.group(1)
                if subdir not in _INTERNAL_SUBDIRS:
                    return subdir
        except Exception:
            pass
    return None


def _infer_testbed_subdir_from_image(image: str) -> Optional[str]:
    """
    Extract the repo subdir from the Docker image name.
    Pattern: sweb.eval.x86_64.<user>_<num>_<repo>-<num>[:<tag>]
    E.g. "…matplotlib_1776_matplotlib-29209:latest" → "matplotlib"
         "…yt-dlp_1776_yt-dlp-12714:latest"        → "yt-dlp"
    """
    m = re.search(r"_(\d+)_([A-Za-z0-9.\-]+)-\d+", image)
    if m:
        return m.group(2)
    return None


def _infer_testbed_subdir(qa_dir: Path, docker_image: str = "") -> str:
    """
    Best-effort inference of /testbed/<subdir> for this repo.
    Priority: question text → Docker image name → repo dir name (minus _qa suffix).
    """
    subdir = _infer_testbed_subdir_from_question(qa_dir)
    if subdir:
        return subdir
    if docker_image:
        subdir = _infer_testbed_subdir_from_image(docker_image)
        if subdir:
            return subdir
    # Fallback: strip common suffixes from repo name
    name = qa_dir.name
    for suffix in ("_qa", "_eval"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name.lower()


def build_repo_configs(
    repo_names: List[str],
    repos_json: Dict[str, str],
) -> List[RepoConfig]:
    configs = []
    for name in repo_names:
        qa_dir = QA_INSTANCES_ROOT / name
        if not qa_dir.is_dir():
            print(f"[{name}] WARNING: qa_instances/{name}/ not found — skipping")
            continue
        docker_image = repos_json.get(name, "")
        if not docker_image:
            print(f"[{name}] WARNING: no Docker image in Repositories.json — will try local install")

        testbed_subdir = _infer_testbed_subdir(qa_dir, docker_image)

        configs.append(RepoConfig(
            name=name,
            docker_image=docker_image,
            qa_dir=qa_dir,
            artifacts_dir=qa_dir / "qa_artifacts",
            sft_dir=SFT_RECORDS_ROOT / name,
            cache_dir=REPO_CACHE_ROOT / name,
            cache_ready=REPO_CACHE_ROOT / name / ".ready",
            testbed_subdir=testbed_subdir,
        ))
    return configs


# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------

def _load_dotenv(path: Path) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip()
    return result


# ---------------------------------------------------------------------------
# Repository setup — Docker copy with local cache
# ---------------------------------------------------------------------------

def get_repo_root(cfg: RepoConfig, *, force_copy: bool = False) -> Optional[Path]:
    """
    Return a local path to the repository for this config.

    Priority:
      1. Cached copy in sft_dataset/repo_cache/<name>/ (unless --force-copy)
      2. Fresh copy from the Docker image
      3. Locally-installed package (fallback)
    """
    if not force_copy and cfg.cache_ready.exists():
        print(f"[{cfg.name}] Repo root: {cfg.cache_dir}  (cached)")
        return cfg.cache_dir

    if cfg.docker_image:
        try:
            runtime = build_container_runtime("docker")
            if runtime.is_available():
                cfg.cache_dir.mkdir(parents=True, exist_ok=True)
                runtime.ensure_image_available(cfg.docker_image, repo_name=cfg.name)
                # Probe the container for the actual repo subdir under /testbed.
                # This is more robust than heuristic name matching and handles
                # images where the repo lives directly at /testbed (returned as ".").
                resolved_subdir = infer_repo_subdir_for_image(
                    cfg.name,
                    cfg.qa_dir,
                    cfg.docker_image,
                    container_runtime=runtime,
                )
                cfg.testbed_subdir = resolved_subdir
                src_dir = "/testbed" if resolved_subdir == "." else f"/testbed/{resolved_subdir}"
                print(f"[{cfg.name}] Copying from Docker: {cfg.docker_image}  ({src_dir})")
                runtime.copy_dir_contents(
                    image=cfg.docker_image,
                    src_dir=src_dir,
                    dest=cfg.cache_dir,
                    name_hint=cfg.name,
                )
                cfg.cache_ready.touch()
                print(f"[{cfg.name}] Repo cached at: {cfg.cache_dir}")
                return cfg.cache_dir
            print(f"[{cfg.name}] Docker not available — falling back to local install")
        except Exception as exc:
            print(f"[{cfg.name}] Docker copy failed ({exc}) — falling back to local install")
    
    return _find_local_package(cfg.testbed_subdir)


def _find_local_package(package_name: str) -> Optional[Path]:
    import subprocess
    try:
        proc = subprocess.run(
            [sys.executable, "-c",
             f"import {package_name}, os; print(os.path.dirname({package_name}.__file__))"],
            capture_output=True, text=True, timeout=15,
        )
        if proc.returncode == 0:
            p = Path(proc.stdout.strip())
            if p.is_dir():
                return p
    except Exception:
        pass
    return None


def remap_testbed_path(raw: str, repo_root: Path, testbed_subdir: str) -> str:
    """Translate /testbed/<subdir>/<rest> paths to the local repo cache."""
    prefix = "/testbed/" if testbed_subdir == "." else f"/testbed/{testbed_subdir}/"
    if raw.startswith(prefix):
        rest = raw[len(prefix):]
        remapped = repo_root / rest
        return str(remapped) if remapped.exists() else rest
    if raw.startswith("/testbed/"):
        # Other testbed path — try stripping /testbed/ and resolving from repo root parent
        return str(repo_root.parent / raw[len("/testbed/"):])
    return raw


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def _make_teacher_system_prompt(oracle_answer: Any, trace_log: str = "", extra_note: str = "") -> str:
    """
    System prompt sent to the teacher LLM during generation.
    Oracle answer and execution trace live here — they guide exploration but are
    NOT saved into the student training messages.
    """
    oracle_str = json.dumps(oracle_answer, indent=2, ensure_ascii=False)
    base = f"""\
You are an expert software engineer creating high-quality SFT training examples \
for a smaller AI model that will learn to analyze runtime behavior of Python codebases.

The student model that trains on your trajectory does NOT see this system prompt, \
the oracle answer, or the execution trace — it sees only the question, the answer \
template, instance files, and the tool results you produce.  Your task is to \
generate a trajectory that demonstrates HOW a skilled engineer DISCOVERS the \
correct answer through systematic code reading.

═══════════════════════════════════════════════════════
CORRECT ANSWER  (use this to guide your investigation)
═══════════════════════════════════════════════════════
{oracle_str}

═══════════════════════════════════════════════════════
EXECUTION TRACE  (private background knowledge — do NOT cite or quote)
═══════════════════════════════════════════════════════
Format: TIMESTAMP  FILE:LINE  QUALIFIED_FUNC  event=TYPE  [retval=VALUE]  locals={{...}}

{trace_log}

═══════════════════════════════════════════════════════
HOW TO USE THE EXECUTION TRACE  ← read this carefully
═══════════════════════════════════════════════════════

The execution trace is your PRIVATE BACKGROUND KNOWLEDGE, not evidence to cite.

It tells you:
  • which function was called with which arguments
  • which branch of the code was actually taken at runtime
  • what values local variables held at key moments

Use this knowledge ONLY to decide which source files to read and which code
path to explain.  NEVER quote a trace line.  NEVER say "the trace shows",
"according to the trace", "trace entry at FILE:LINE", or anything like it.

Your written reasoning must be derived entirely from the source code you read
via read_file.  Think of the trace as a whisper from a senior engineer that
tells you exactly where to look — but everything you write in your messages
must come from reading the code, not from quoting that whisper.

────────────────────────────────────────────────────
CONCRETE EXAMPLES — right vs wrong
────────────────────────────────────────────────────

Suppose the question asks: "What does add(2, 3) return?"
The trace shows: retval=5

  ✗ WRONG — citing the trace directly:
      "The trace shows the return value was 5."
      "According to trace entry add:42 retval=5, the function returned 5."
      "The trace records locals={{a: 2, b: 3}} so the result is 5."

  ✓ CORRECT — deriving the answer from the code:
      "Looking at `add(a, b)` in math.py: the function body is `return a + b`.
       For the test inputs a=2, b=3 this evaluates to 2 + 3 = 5."

Suppose the question asks about which branch a conditional takes:

  ✗ WRONG:
      "The trace shows the if-branch was taken, so x must be positive."

  ✓ CORRECT:
      "The test passes x=5. The condition `if x > 0` on line 14 is True for
       x=5, so execution enters the if-branch which returns x * 2 = 10."

Suppose the question asks about a list built up during a loop:

  ✗ WRONG:
      "Trace entries show c_part received [6, x, z, y**2] before the return."

  ✓ CORRECT:
      "For each commutative factor in seq, flatten() calls as_base_exp() and
       collects (base, exp) pairs in c_powers. For the inputs 6, x, z, y**2,
       the numeric factor 6 is folded into coeff, while x, z, y**2 are stored
       as symbolic factors. After _gather() and _mulsort(), c_part is
       [6, x, z, y**2] in canonical order."

═══════════════════════════════════════════════════════
WORKFLOW
═══════════════════════════════════════════════════════

1. Study the correct answer and the question. Identify which function and
   which moment in execution is being asked about.

2. Consult the trace PRIVATELY to know which arguments were passed and which
   code path executed. Use that to decide which files to read.

3. Use read_file and list_dir to read the relevant source code. Navigate from
   the instance files (files/tests/qa/) → the called function → implementation.

4. In EVERY assistant message during exploration, write explicit code-based
   reasoning:
   — what function / data structure you are reading and what you found
   — how the code logic processes the specific test inputs, step by step
   — what the code produces and why, referencing specific lines you read
   — what you will read next and why

5. Make ONLY tool calls that are directly relevant. Avoid unnecessary files.

6. When you have read all the relevant code:  {TOOL_PHASE_DONE_SENTINEL}

7. After the follow-up prompt, return ONLY the raw JSON answer — no markdown,
   no explanations.

═══════════════════════════════════════════════════════
QUALITY REQUIREMENTS
═══════════════════════════════════════════════════════

• Never quote or mention the execution trace
• Every claim about a runtime value must follow logically from source code read
• A reader with no trace access must be able to follow and verify your reasoning
• Reasoning must form a complete chain: question → code logic → value
• Tool calls must represent the minimal sufficient investigation
• Final answer: raw JSON only — no markdown, no headings
"""
    if extra_note:
        base += f"\n\nNOTE: {extra_note}"
    return base


# Student system prompt — saved into training data, matches eval-time format exactly
# (mirrors make_system_prompt(repo_map_mode="none") from run_llm_repomap_eval_host.py)
STUDENT_SYSTEM_PROMPT = (
    "Solve repository QA in read-only mode with tool calls only.\n"
    "Rules:\n"
    "1. Use list_dir/read_file tools only (get_repo_map is disabled).\n"
    "2. Prefer relative paths. Repo files are usually like src/...; instance files are usually files/....\n"
    "3. Minimize unnecessary reads and repeated failed paths.\n"
    f"4. read_file has a hard per-call limit: at most {MAX_READ_LINES} lines.\n"
    f"5. When you are completely done using tools, reply with exactly {TOOL_PHASE_DONE_SENTINEL}.\n"
    "6. Do not combine the completion signal with the final JSON answer.\n"
    "7. After the follow-up prompt closes the tool phase, return exactly one JSON object matching "
    "template_answer keys and value types.\n"
    "8. Do not output markdown or explanations in the final answer."
)


def _make_user_prompt(
    *,
    question: str,
    question_kind: str,
    template_answer: Any,
    repo_root: Path,
    instance_dir: Path,
) -> str:
    """
    User message shared between teacher and student contexts.
    Matches build_user_prompt() from run_llm_repomap_eval_host.py exactly — no trace,
    no test file content inline. The trace is private in the teacher system prompt only.
    """
    template_str = json.dumps(template_answer, sort_keys=True, separators=(",", ":"))

    files_dir = instance_dir / "files"
    instance_files: List[str] = []
    if files_dir.exists():
        instance_files = [
            str(p.relative_to(instance_dir))
            for p in sorted(files_dir.rglob("*"))
            if p.is_file()
        ]

    preview_files = instance_files[:INSTANCE_PREVIEW_LIMIT]
    preview_lines = [f"- {p}" for p in preview_files]
    omitted = len(instance_files) - len(preview_files)
    if omitted > 0:
        preview_lines.append(f"- ... ({omitted} more files)")
    preview_str = "\n".join(preview_lines)

    return (
        f"Repository root: {repo_root}\n"
        f"Instance directory: {instance_dir}\n"
        f"Question kind: {question_kind}\n\n"
        f"Question:\n{question}\n\n"
        f"Template answer (must match exactly):\n{template_str}\n\n"
        "Instance file preview (you can read these and repository files with tools):\n"
        f"{preview_str if preview_str else '- (no files)'}\n\n"
        f"Task phase 1: use tools as needed, then reply with exactly {TOOL_PHASE_DONE_SENTINEL}.\n"
        "Task phase 2: after the follow-up closes tool use, return only the final JSON answer object."
    )


# Matches FINAL_JSON_PROMPT from provider_runner.py — raw JSON, no markdown
_STRUCTURED_FINAL_PROMPT = FINAL_JSON_PROMPT

# ---------------------------------------------------------------------------
# Answer extraction and validation
# ---------------------------------------------------------------------------

def extract_answer_from_response(response_text: str) -> Optional[Any]:
    match = re.search(r"##\s*Answer\s*\n+(.*)", response_text, re.DOTALL | re.IGNORECASE)
    candidate = match.group(1).strip() if match else response_text

    candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.MULTILINE)
    candidate = re.sub(r"\s*```$", "", candidate, flags=re.MULTILINE)
    candidate = candidate.strip()

    for pat in (r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", r"\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]"):
        hits = list(re.finditer(pat, candidate, re.DOTALL))
        if hits:
            try:
                return json.loads(hits[-1].group())
            except json.JSONDecodeError:
                pass

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    for end in range(len(response_text) - 1, -1, -1):
        if response_text[end] in ('}', ']'):
            for start in range(end, -1, -1):
                if response_text[start] in ('{', '['):
                    try:
                        return json.loads(response_text[start:end + 1])
                    except json.JSONDecodeError:
                        continue
            break
    return None


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, float) and value == int(value):
        return int(value)
    if isinstance(value, str):
        return value.strip()
    return value


def answers_match(predicted: Any, oracle: Any) -> bool:
    try:
        return _normalize(predicted) == _normalize(oracle)
    except Exception:
        return str(predicted) == str(oracle)


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

def _parse_args(raw_json: str) -> Dict[str, Any]:
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError:
        return {}


def dispatch_tool(
    name: str,
    raw_args: Dict[str, Any],
    tools_handler: ReadOnlyRepoTools,
    repo_root: Optional[Path],
    testbed_subdir: str,
) -> Dict[str, Any]:
    args = dict(raw_args)
    if repo_root and "path" in args:
        args["path"] = remap_testbed_path(str(args["path"]), repo_root, testbed_subdir)

    if name == "read_file":
        result = tools_handler.read_file(
            path=str(args.get("path", "")),
            start_line=int(args.get("start_line", 1)),
            end_line=args.get("end_line"),
        )
    elif name == "list_dir":
        result = tools_handler.list_dir(
            path=str(args.get("path", ".")),
            max_entries=int(args.get("max_entries", 200)),
        )
    else:
        return {"ok": False, "error": f"Unknown tool: {name!r}"}

    payload = shrink_tool_payload_for_llm(name, result.payload)
    return {"ok": result.ok, **payload}


# ---------------------------------------------------------------------------
# OpenAI call helpers
# ---------------------------------------------------------------------------

def _is_reasoning_model(model: str) -> bool:
    return bool(re.match(r"^o\d", model.lower()))


def _chat(client: openai.OpenAI, model: str, messages: List[Dict], **extra) -> Any:
    kwargs: Dict[str, Any] = dict(model=model, messages=messages, **extra)
    if not _is_reasoning_model(model) and "temperature" not in kwargs:
        kwargs["temperature"] = 0.3
    return client.chat.completions.create(**kwargs)


def _chat_final(client: openai.OpenAI, model: str, messages: List[Dict]) -> Any:
    kwargs: Dict[str, Any] = dict(model=model, messages=messages)
    if not _is_reasoning_model(model):
        kwargs["temperature"] = 0.0
    return client.chat.completions.create(**kwargs)


# ---------------------------------------------------------------------------
# Agentic loop
# ---------------------------------------------------------------------------

def _is_done(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", (text or "")).strip().lower()
    markers = [
        TOOL_PHASE_DONE_SENTINEL.lower(),
        TOOL_PHASE_DONE_SENTINEL.lower().replace("_", " "),
        "done with file reading",
        "done reading files",
        "finished reading files",
        "finished with file reading",
    ]
    return any(m in normalized for m in markers)


def run_agentic_loop(
    client: openai.OpenAI,
    model: str,
    messages: List[Dict[str, Any]],
    tools_handler: ReadOnlyRepoTools,
    repo_root: Optional[Path],
    testbed_subdir: str,
    max_rounds: int = MAX_TOOL_ROUNDS,
) -> List[Dict[str, Any]]:
    tool_calls_made = 0

    while tool_calls_made < max_rounds:
        resp = _chat(client, model, messages, tools=TOOLS, tool_choice="auto")
        msg = resp.choices[0].message
        content_text: str = msg.content or ""

        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": content_text}
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_msg)

        if not msg.tool_calls:
            if _is_done(content_text):
                break
            messages.append({"role": "user", "content": TOOL_PHASE_REMINDER_PROMPT})
            continue

        for tc in msg.tool_calls:
            raw_args = _parse_args(tc.function.arguments)
            result_payload = dispatch_tool(
                tc.function.name, raw_args, tools_handler, repo_root, testbed_subdir
            )
            tool_calls_made += 1
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.function.name,
                "content": json.dumps(result_payload, ensure_ascii=False),
            })

    return messages


# ---------------------------------------------------------------------------
# Single attempt
# ---------------------------------------------------------------------------

def _attempt(
    client: openai.OpenAI,
    model: str,
    question: str,
    question_kind: str,
    template_answer: Any,
    oracle_answer: Any,
    trace_log: str,
    tools_handler: ReadOnlyRepoTools,
    repo_root: Path,
    instance_dir: Path,
    testbed_subdir: str,
    extra_note: str = "",
) -> Tuple[List[Dict[str, Any]], Optional[Any]]:
    """
    Run one full attempt (agentic phase + structured final response).

    Teacher context: oracle + trace in system prompt (guides exploration, NOT saved).
    User message: eval-style (question + template + instance files, no trace).
    Saved student messages: swap system → eval-style system prompt; all other turns kept.

    Returns (student_messages, extracted_answer).
    """
    user_content = _make_user_prompt(
        question=question,
        question_kind=question_kind,
        template_answer=template_answer,
        repo_root=repo_root,
        instance_dir=instance_dir,
    )

    # Teacher context: oracle + trace in system (guides generation, NOT saved)
    teacher_messages: List[Dict[str, Any]] = [
        {"role": "system", "content": _make_teacher_system_prompt(oracle_answer, trace_log, extra_note)},
        {"role": "user", "content": user_content},
    ]

    teacher_messages = run_agentic_loop(
        client=client,
        model=model,
        messages=teacher_messages,
        tools_handler=tools_handler,
        repo_root=repo_root,
        testbed_subdir=testbed_subdir,
    )

    teacher_messages.append({"role": "user", "content": _STRUCTURED_FINAL_PROMPT})

    final_resp = _chat_final(client, model, teacher_messages)
    final_content = final_resp.choices[0].message.content or ""
    teacher_messages.append({"role": "assistant", "content": final_content})

    extracted = extract_answer_from_response(final_content)

    # Build student training messages: swap system to oracle-free student prompt
    student_messages: List[Dict[str, Any]] = [
        {"role": "system", "content": STUDENT_SYSTEM_PROMPT},
        *teacher_messages[1:],  # keep all user/assistant/tool turns as-is
    ]

    return student_messages, extracted


# ---------------------------------------------------------------------------
# Per-instance processing
# ---------------------------------------------------------------------------

def process_instance(
    client: openai.OpenAI,
    model: str,
    instance_id: str,
    cfg: RepoConfig,
    max_tool_rounds: int = MAX_TOOL_ROUNDS,
) -> Optional[Dict[str, Any]]:
    instance_dir = cfg.qa_dir / instance_id
    artifacts_dir = cfg.artifacts_dir / instance_id

    # oracle.json
    oracle_path = instance_dir / "oracle.json"
    if not oracle_path.exists():
        print(f"  [{cfg.name}/{instance_id}] skip — no oracle.json")
        return None
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    question: str = oracle.get("question", "")
    template_answer: Any = oracle.get("template_answer", {})
    oracle_answer: Any = oracle.get("oracle_answer", {})
    question_kind: str = oracle.get("question_kind", "unknown")

    # trace.log
    trace_path = artifacts_dir / "trace.log"
    if not trace_path.exists():
        print(f"  [{cfg.name}/{instance_id}] skip — no trace.log")
        return None
    trace_size = trace_path.stat().st_size
    if trace_size > MAX_TRACE_BYTES:
        print(f"  [{cfg.name}/{instance_id}] skip — trace too large "
              f"({trace_size / 1_048_576:.1f} MB)")
        return None
    trace_log = trace_path.read_text(encoding="utf-8", errors="replace")

    # repo check
    if cfg.repo_root is None or not cfg.repo_root.exists():
        print(f"  [{cfg.name}/{instance_id}] skip — repo not found at {cfg.repo_root}")
        return None

    tools_handler = ReadOnlyRepoTools(
        repo_root=cfg.repo_root,
        instance_dir=instance_dir,
        max_read_lines=MAX_READ_LINES,
        repo_map_mode="none",
    )

    tag = f"{cfg.name}/{instance_id}"

    # Attempt 1
    print(f"  [{tag}] attempt 1 …")
    messages, extracted = _attempt(
        client=client,
        model=model,
        question=question,
        question_kind=question_kind,
        template_answer=template_answer,
        oracle_answer=oracle_answer,
        trace_log=trace_log,
        tools_handler=tools_handler,
        repo_root=cfg.repo_root,
        instance_dir=instance_dir,
        testbed_subdir=cfg.testbed_subdir,
    )

    if extracted is not None and answers_match(extracted, oracle_answer):
        print(f"  [{tag}] correct on attempt 1")
        return _make_record(instance_id, cfg, question_kind, messages, attempt=1)

    print(f"  [{tag}] wrong on attempt 1  (got: {json.dumps(extracted)[:120]})")

    # Attempt 2
    print(f"  [{tag}] attempt 2 …")
    note = (
        "Your previous attempt produced an answer that did not match the expected "
        "template structure. Study the correct answer and the template carefully, "
        "re-read the relevant source code, and ensure every key and value in your "
        "final JSON exactly matches the template structure and the correct answer. "
        "Derive each value from the code logic — walk through the data flow and "
        "return statements for the exact inputs from the test."
    )
    messages2, extracted2 = _attempt(
        client=client,
        model=model,
        question=question,
        question_kind=question_kind,
        template_answer=template_answer,
        oracle_answer=oracle_answer,
        trace_log=trace_log,
        tools_handler=tools_handler,
        repo_root=cfg.repo_root,
        instance_dir=instance_dir,
        testbed_subdir=cfg.testbed_subdir,
        extra_note=note,
    )

    if extracted2 is not None and answers_match(extracted2, oracle_answer):
        print(f"  [{tag}] correct on attempt 2")
        return _make_record(instance_id, cfg, question_kind, messages2, attempt=2)

    print(f"  [{tag}] discarding — wrong after 2 attempts")
    return None


def _make_record(
    instance_id: str,
    cfg: RepoConfig,
    question_kind: str,
    messages: List[Dict[str, Any]],
    attempt: int,
) -> Dict[str, Any]:
    record = {
        "repo": cfg.name,
        "instance_id": instance_id,
        "question_kind": question_kind,
        "attempt": attempt,
        "messages": messages,
    }
    cfg.sft_dir.mkdir(parents=True, exist_ok=True)
    out = cfg.sft_dir / f"{instance_id}.json"
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


# ---------------------------------------------------------------------------
# Instance enumeration
# ---------------------------------------------------------------------------

def _enumerate_instances(qa_dir: Path, explicit: Optional[List[str]]) -> List[str]:
    if explicit:
        return explicit
    return sorted(
        d.name
        for d in qa_dir.iterdir()
        if d.is_dir()
        and not d.name.startswith(".")
        and d.name not in _SKIP_DIRS
        and not d.name.endswith(".sh")
    )


def _available_repos() -> List[str]:
    return sorted(
        d.name
        for d in QA_INSTANCES_ROOT.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def _expand_repo_cli_args(repo_values: Optional[List[str]]) -> Optional[List[str]]:
    """Turn --repo CLI values into a flat list of names (comma-separated + multiple args)."""
    if not repo_values:
        return None
    names: List[str] = []
    for raw in repo_values:
        for part in str(raw).split(","):
            name = part.strip()
            if name:
                names.append(name)
    return names or None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    available = _available_repos()

    parser = argparse.ArgumentParser(
        description="Generate SFT dataset via oracle-guided agentic trajectories"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"OpenAI model (default: {DEFAULT_MODEL})")
    parser.add_argument("--api-key", default=None,
                        help="OpenAI API key (overrides env / .env)")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help=f"Parallel worker threads (default: {DEFAULT_WORKERS})")
    parser.add_argument("--max-tool-rounds", type=int, default=MAX_TOOL_ROUNDS,
                        help=f"Max tool-call rounds per attempt (default: {MAX_TOOL_ROUNDS})")
    parser.add_argument("--force-copy", action="store_true",
                        help="Re-copy repo from Docker even if cache exists")
    parser.add_argument(
        "--repo", nargs="*", metavar="REPO", default=None,
        help=(
            f"Repo name(s): comma-separated list and/or multiple values (default: all). "
            f"Example: --repo A,B or --repo A B. Available: {', '.join(available)}"
        ),
    )
    parser.add_argument("--instances", nargs="*", metavar="ID",
                        help="Specific instance IDs (only valid when --repo names a single repo)")
    args = parser.parse_args()

    repo_names_arg = _expand_repo_cli_args(args.repo)
    if args.instances and repo_names_arg and len(repo_names_arg) != 1:
        parser.error("--instances requires exactly one repo via --repo")

    # API key: CLI > env var > .env file
    env_vars = _load_dotenv(_SCRIPT_DIR / ".env")
    api_key = (
        args.api_key
        or os.environ.get("OPENAI_API_KEY")
        or env_vars.get("openai_api_key")
    )
    if not api_key:
        parser.error(
            "OpenAI API key not found. Provide --api-key, set OPENAI_API_KEY, "
            "or add openai_api_key=sk-... to the project .env file."
        )

    client = openai.OpenAI(api_key=api_key)
    repos_json = _load_repos_json()

    repo_names = repo_names_arg if repo_names_arg else available
    repo_configs = build_repo_configs(repo_names, repos_json)
    if not repo_configs:
        print("No valid repos found. Aborting.")
        sys.exit(1)

    # Copy repos (sequentially to avoid Docker conflicts)
    for cfg in repo_configs:
        cfg.repo_root = get_repo_root(cfg, force_copy=args.force_copy)
        if cfg.repo_root is None:
            print(f"[{cfg.name}] WARNING: Could not obtain repo — instances will be skipped")

    print(f"\nModel    : {args.model}")
    print(f"Workers  : {args.workers}")
    print(f"Repos    : {[c.name for c in repo_configs]}")
    print(f"Output   : {SFT_RECORDS_ROOT}/<repo>/<instance>.json\n")

    n_ok = n_skip = n_discard = n_err = 0
    _counter_lock = threading.Lock()

    for cfg in repo_configs:
        instance_ids = _enumerate_instances(cfg.qa_dir, args.instances)
        print(f"[{cfg.name}] {len(instance_ids)} instances  testbed=/{cfg.testbed_subdir}/  "
              f"repo={'OK' if cfg.repo_root else 'MISSING'}")

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(
                    process_instance,
                    client, args.model, inst_id, cfg, args.max_tool_rounds,
                ): inst_id
                for inst_id in instance_ids
            }

            for future in as_completed(futures):
                inst_id = futures[future]
                try:
                    record = future.result()
                    with _counter_lock:
                        if record is None:
                            oracle_f = cfg.qa_dir / inst_id / "oracle.json"
                            trace_f = cfg.artifacts_dir / inst_id / "trace.log"
                            if (
                                oracle_f.exists()
                                and trace_f.exists()
                                and trace_f.stat().st_size <= MAX_TRACE_BYTES
                            ):
                                n_discard += 1
                            else:
                                n_skip += 1
                        else:
                            n_ok += 1
                            print(
                                f"  [{cfg.name}/{inst_id}] saved  "
                                f"({len(record['messages'])} msgs, "
                                f"attempt {record['attempt']})"
                            )
                except Exception as exc:
                    with _counter_lock:
                        n_err += 1
                    import traceback
                    print(f"  [{cfg.name}/{inst_id}] ERROR: {exc}")
                    traceback.print_exc()

    print()
    print("=" * 58)
    print(f"Saved    (correct) : {n_ok}")
    print(f"Skipped (no data)  : {n_skip}")
    print(f"Discarded (wrong)  : {n_discard}")
    print(f"Errors             : {n_err}")
    print(f"Per-file dir       : {SFT_RECORDS_ROOT}/")


if __name__ == "__main__":
    main()
