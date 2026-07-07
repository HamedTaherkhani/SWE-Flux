"""LLM-based input perturbation (source-level).

Unlike the AST strategies (which mutate individual numeric literals), this asks
an LLM to rewrite a test's *concrete input values* -- any type, not just
numbers -- while preserving the test's structure (imports, class/method names,
call order, assertions). The model is told to target edge cases that exercise
new branches of the function under test, and it can use read-only repository
tools (``get_repo_map`` / ``list_dir`` / ``read_file``) to inspect that function
first -- the same tools the LLM evaluation uses, reused from ``repo_tools.py``.

It produces N candidate perturbed test sources per instance; the pipeline then
harvests + gates each exactly like the AST candidates, so the LLM is only a
smarter *proposer* -- the oracle and validation are unchanged.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .paths import ensure_repo_on_path

ensure_repo_on_path()
from evaluation_scripts.llm_eval.provider_runner import ProviderRunner  # noqa: E402
from evaluation_scripts.llm_eval.repo_tools import (  # noqa: E402
    ReadOnlyRepoTools,
    shrink_tool_payload_for_llm,
)

VARIANT_SEPARATOR = "===PERTURBATION==="

_SYSTEM_PROMPT = """\
You generate perturbed variants of a Python pytest test to build *harder* test \
instances for evaluating code-reasoning models.

Hard rules -- a variant is invalid if it breaks any of these:
1. Change ONLY concrete input values/literals: numbers, strings, lists/arrays, \
dicts, tuples, keyword-argument values, and constructor arguments that represent \
DATA.
2. Preserve the test STRUCTURE exactly: keep all imports, the class name, the \
method/function names, their signatures, the order and identity of all calls, \
and the presence of every assertion. Do not add or remove statements.
3. Every variant must be VALID, RUNNABLE Python that executes the same functions \
on the new inputs without raising (avoid out-of-domain values that crash, e.g. \
month=13, negative sizes, mismatched array shapes, indices out of range).
4. Choose inputs that hit EDGE CASES and cross DIFFERENT BRANCHES of the function \
under test than the original input does (e.g. values just below / at / above the \
function's comparison thresholds, empty vs non-empty, zero / sign changes, \
boundary lengths). Use the tools to read the function under test first and find \
its branch conditions.

Use the read-only tools (get_repo_map, list_dir, read_file) to inspect the \
function under test before deciding on inputs. When done exploring, output the \
variants.

Output format: emit exactly N complete perturbed test files, each being the FULL \
file content, separated by a line containing only:
{sep}
Do not include explanations or markdown fences -- only the file contents and the \
separators between them.
"""

_USER_PROMPT = """\
Target test file (relative path): {test_path}
Function(s) under test to target (from the harness trace config):
  TRACE_FILE: {trace_file}
  TRACE_FUNC: {trace_func}

Produce exactly {n} perturbed variants of the test below, following all rules. \
Each variant must keep the same class/method names and structure, changing only \
the concrete input values to target new branches/edge cases of the function(s) \
under test.

----- ORIGINAL TEST FILE -----
{source}
----- END ORIGINAL TEST FILE -----
"""


_FINAL_VARIANTS_PROMPT = """\
You already signaled DONE_WITH_FILE_READING. Tool phase is closed.
Return ONLY the requested complete Python test file variant(s), separated by
the required separator line if more than one variant is requested. Do not output
JSON, markdown fences, or explanations.
"""


@dataclass
class LLMPerturbationConfig:
    provider: str = "openai"
    model: str = "gpt-5.4-2026-03-05"
    n: int = 5
    temperature: float = 0  # some diversity across variants
    max_read_lines: int = 300
    repo_map_mode: str = "repomap" 


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_]*\n", "", t)
        if t.endswith("```"):
            t = t[: -3]
    return t.strip()


class LLMPerturber:
    """Generates N structure-preserving perturbed test sources via an LLM."""

    def __init__(self, config: LLMPerturbationConfig, trace: Optional[Callable[[str], None]] = None) -> None:
        self.config = config
        self.trace = trace

    def _t(self, msg: str) -> None:
        if self.trace:
            self.trace(msg)

    def _make_tool_callback(self, tools: ReadOnlyRepoTools) -> Callable[[str, Dict], Dict]:
        def tool_callback(name: str, args: Dict) -> Dict:
            if name == "get_repo_map":
                res = tools.get_repo_map(focus_paths=args.get("focus_paths"))
            elif name == "list_dir":
                res = tools.list_dir(path=args.get("path", "."), max_entries=args.get("max_entries", 200))
            elif name == "read_file":
                res = tools.read_file(
                    path=args.get("path", ""),
                    start_line=args.get("start_line", 1),
                    end_line=args.get("end_line", 250),
                )
            else:
                return {"ok": False, "error": f"unknown tool: {name}"}
            out = {"ok": res.ok, **res.payload}
            return shrink_tool_payload_for_llm(name, out)

        return tool_callback

    def generate_variants(
        self,
        *,
        original_source: str,
        test_rel_path: str,
        trace_file: str,
        trace_funcs: List[str],
        repo_root: Path,
        instance_dir: Path,
        n: Optional[int] = None,
    ) -> List[str]:
        """Return up to ``n`` valid, structure-preserving perturbed sources."""
        n = n or self.config.n

        tools = ReadOnlyRepoTools(
            repo_root=repo_root,
            instance_dir=instance_dir,
            max_read_lines=self.config.max_read_lines,
            repo_map_mode=self.config.repo_map_mode,
        )
        runner = ProviderRunner(
            provider=self.config.provider,
            model=self.config.model,
            temperature=self.config.temperature,
            trace=self.trace,
            final_answer_prompt=_FINAL_VARIANTS_PROMPT,
        )

        system_prompt = _SYSTEM_PROMPT.format(sep=VARIANT_SEPARATOR)
        user_prompt = _USER_PROMPT.format(
            test_path=test_rel_path,
            trace_file=trace_file or "(not set)",
            trace_func=", ".join(trace_funcs) or "(not set)",
            n=n,
            source=original_source,
        )

        try:
            raw = runner.run(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tool_callback=self._make_tool_callback(tools),
                tool_names=tools.enabled_tool_names(),
            )
        except Exception as exc:  # noqa: BLE001
            self._t(f"[llm-perturb] generation failed: {exc}")
            return []

        return self._parse_variants(raw, original_source, n)

    def _parse_variants(self, raw: str, original_source: str, n: int) -> List[str]:
        """Split the response into variants and keep valid, changed, well-formed ones."""
        # Some models wrap the whole thing in JSON {"variants": [...]}; support both.
        variants: List[str] = []
        stripped = raw.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                data = json.loads(stripped)
                if isinstance(data, dict) and isinstance(data.get("variants"), list):
                    variants = [str(v) for v in data["variants"]]
                elif isinstance(data, list):
                    variants = [str(v) for v in data]
            except Exception:  # noqa: BLE001
                variants = []
        if not variants:
            parts = raw.split(VARIANT_SEPARATOR)
            variants = [p for p in (s.strip() for s in parts) if p]

        out: List[str] = []
        seen: set = set()
        for v in variants:
            src = _strip_code_fences(v)
            if not src or src in seen:
                continue
            if src.strip() == original_source.strip():
                continue  # no-op
            try:
                ast.parse(src)  # must be valid Python
            except SyntaxError:
                self._t("[llm-perturb] dropped a variant: invalid Python")
                continue
            seen.add(src)
            out.append(src)
            if len(out) >= n:
                break
        self._t(f"[llm-perturb] kept {len(out)}/{len(variants)} variants")
        return out
