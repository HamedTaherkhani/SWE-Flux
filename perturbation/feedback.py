"""Post-process non-flipping perturbations with LLM feedback.

This module is intentionally separate from the initial perturbation pipeline.
It reads a completed perturbation report, copies already-successful flips into
a new output tree, and then runs a bounded feedback loop for generated
instances that did not flip the target model.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .config import PerturbationConfig
from .coverage import CoverageExtractor, CoverageSignature
from .llm_strategy import LLMPerturbationConfig, VARIANT_SEPARATOR, _strip_code_fences
from .models import InstanceOutcome
from .paths import DEFAULT_OUTPUT_ROOT, OutputLayout, RepoLayout, ensure_repo_on_path
from .pipeline import PerturbationPipeline

ensure_repo_on_path()
from evaluation_scripts import evaluate_qa_answers as eqa  # noqa: E402
from evaluation_scripts.llm_eval.provider_runner import ProviderRunner  # noqa: E402
from evaluation_scripts.llm_eval.repo_tools import (  # noqa: E402
    ReadOnlyRepoTools,
    shrink_tool_payload_for_llm,
)


_SYSTEM_PROMPT = """\
You are improving an existing input perturbation that did NOT flip the target \
model. Generate a stronger structure-preserving pytest test variant.

Hard rules:
1. Change ONLY concrete input values/literals: numbers, strings, lists/arrays, \
dicts, tuples, keyword values, and constructor arguments that represent DATA.
2. Preserve test STRUCTURE exactly: imports, class/function names, signatures, \
statement order, call identities, and assertions must remain present.
3. The variant must be valid runnable Python and should still reach the behavior \
under test without unrelated setup errors.
4. Use the original and current execution-path/oracle feedback below. If the \
current execution path is the same as the original, choose valid inputs likely \
to hit a different branch/path. If the oracle is unchanged, choose valid inputs \
that are likely to change the harvested oracle answer. If the oracle already \
changed but the model still passed, move to a nearby valid case that stresses \
the same task more strongly.
5. Use repository read tools before deciding on values when target source \
context is needed.

Output format: emit exactly one complete Python test file. Do not include \
markdown fences or explanations.
"""


_USER_PROMPT = """\
Target test file: {test_path}
TRACE_FILE: {trace_file}
TRACE_FUNC: {trace_func}
Task/question:
{question}

Feedback status:
- Current candidate did not flip the model.
- Exact execution path same as original: {same_trace}
- Oracle changed from original: {oracle_changed}
- Original model result: {original_model_result}
- Current perturbed model result: {current_model_result}

Original oracle answer:
{original_oracle}

Current perturbed oracle answer:
{current_oracle}

Original execution path summary:
{original_trace}

Current perturbed execution path summary:
{current_trace}

Original test file:
----- ORIGINAL TEST FILE -----
{original_source}
----- END ORIGINAL TEST FILE -----

Current non-flipping perturbed test file:
----- CURRENT PERTURBED TEST FILE -----
{current_source}
----- END CURRENT PERTURBED TEST FILE -----

Generate one improved perturbed test file. Preserve structure and change only \
concrete input values.
"""


_FINAL_SOURCE_PROMPT = """\
You already signaled DONE_WITH_FILE_READING. Tool phase is closed.
Return ONLY one complete Python test file, with no markdown fences and no
explanations. Preserve the original test structure exactly and change only
concrete input values.
"""


def _json_compact(value: object, limit: int = 5000) -> str:
    try:
        text = json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except TypeError:
        text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... <truncated>"


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _oracle_answer(path: Path) -> object:
    data = _load_json(path)
    if isinstance(data, dict):
        return data.get("oracle_answer")
    return None


def _question(path: Path) -> str:
    data = _load_json(path)
    if isinstance(data, dict):
        return str(data.get("question") or "")
    return ""


def _question_kind(path: Path) -> str:
    data = _load_json(path)
    if isinstance(data, dict):
        return str(data.get("question_kind") or "UNKNOWN")
    return "UNKNOWN"


def _event_summary(sig: Optional[CoverageSignature], *, limit: int = 220) -> str:
    if not sig:
        return "(no parseable trace events)"
    events = list(sig.events)
    lines = sorted(sig.lines)
    header = [
        f"events={len(events)} unique_lines={len(sig.lines)} unique_edges={len(sig.edges)}",
        "unique_lines_sample="
        + _json_compact([f"{path}:{line}" for path, line in lines[:80]], limit=2500),
    ]
    if len(events) <= limit:
        shown = events
    else:
        head = events[: int(limit * 0.75)]
        tail = events[-(limit - len(head)) :]
        shown = head + [("<truncated>", -1, "<truncated>", "<truncated>")] + tail
    body = [f"{path}:{line} {func} event={event}" for path, line, func, event in shown]
    return "\n".join(header + body)


def _stage_ok(outcome: InstanceOutcome, name: str) -> bool:
    return any(stage.name == name and stage.ok for stage in outcome.stages)


@dataclass
class FeedbackSourceResult:
    repo: str
    original_id: str
    start_new_id: str
    input_row: Optional[dict] = None
    attempts: List[InstanceOutcome] = field(default_factory=list)
    success_new_id: Optional[str] = None
    retained_new_id: Optional[str] = None
    retained_source: Optional[str] = None
    fallback_row: Optional[dict] = None

    @property
    def succeeded(self) -> bool:
        return self.success_new_id is not None

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "original_id": self.original_id,
            "start_new_id": self.start_new_id,
            "success_new_id": self.success_new_id,
            "retained_new_id": self.retained_new_id,
            "retained_source": self.retained_source,
            "succeeded": self.succeeded,
            "fallback_retained": self.fallback_row,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
        }


class FeedbackPerturber:
    """LLM proposer for one feedback-improved source."""

    def __init__(self, config: LLMPerturbationConfig, trace: Optional[Callable[[str], None]] = None) -> None:
        self.config = config
        self.trace = trace
        self.last_error: str = ""

    def _t(self, msg: str) -> None:
        if self.trace:
            self.trace(msg)

    def _make_tool_callback(self, tools: ReadOnlyRepoTools) -> Callable[[str, Dict], Dict]:
        def tool_callback(name: str, args: Dict) -> Dict:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
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
            return shrink_tool_payload_for_llm(name, {"ok": res.ok, **res.payload})

        return tool_callback

    def generate(
        self,
        *,
        original_source: str,
        current_source: str,
        test_rel_path: str,
        trace_file: str,
        trace_funcs: List[str],
        repo_root: Path,
        instance_dir: Path,
        original_oracle: object,
        current_oracle: object,
        question: str,
        question_kind: str,
        original_trace: Optional[CoverageSignature],
        current_trace: Optional[CoverageSignature],
        same_trace: Optional[bool],
        oracle_changed: Optional[bool],
        original_model_result: str,
        current_model_result: str,
    ) -> Optional[str]:
        self.last_error = ""
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
            final_answer_prompt=_FINAL_SOURCE_PROMPT,
        )
        prompt = _USER_PROMPT.format(
            test_path=test_rel_path,
            trace_file=trace_file or "(not set)",
            trace_func=", ".join(trace_funcs) or "(not set)",
            question_kind=question_kind,
            question=question or "(not available)",
            same_trace={True: "yes", False: "no", None: "unknown"}[same_trace],
            oracle_changed={True: "yes", False: "no", None: "unknown"}[oracle_changed],
            original_model_result=original_model_result,
            current_model_result=current_model_result,
            original_oracle=_json_compact(original_oracle),
            current_oracle=_json_compact(current_oracle),
            original_trace=_event_summary(original_trace),
            current_trace=_event_summary(current_trace),
            original_source=original_source,
            current_source=current_source,
        )
        try:
            raw = runner.run(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=prompt,
                tool_callback=self._make_tool_callback(tools),
                tool_names=tools.enabled_tool_names(),
            )
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"generation failed: {exc}"
            self._t(f"[feedback] {self.last_error}")
            return None
        return self._parse_one(raw, original_source, current_source)

    def _parse_one(self, raw: str, original_source: str, current_source: str) -> Optional[str]:
        text = raw.strip()
        if VARIANT_SEPARATOR in text:
            text = text.split(VARIANT_SEPARATOR, 1)[0]
        if text.startswith("{") or text.startswith("["):
            parsed_variant = False
            try:
                data = json.loads(text)
                if isinstance(data, dict) and isinstance(data.get("variant"), str):
                    text = data["variant"]
                    parsed_variant = True
                elif isinstance(data, dict) and isinstance(data.get("variants"), list) and data["variants"]:
                    text = str(data["variants"][0])
                    parsed_variant = True
                elif isinstance(data, list) and data:
                    text = str(data[0])
                    parsed_variant = True
            except Exception:  # noqa: BLE001
                pass
            if not parsed_variant:
                self.last_error = "JSON response did not contain a variant"
                self._t(f"[feedback] dropped candidate: {self.last_error}")
                return None
        source = _strip_code_fences(text)
        if not source or source.strip() in {original_source.strip(), current_source.strip()}:
            self.last_error = "no source change"
            self._t(f"[feedback] dropped candidate: {self.last_error}")
            return None
        try:
            candidate_tree = ast.parse(source)
            current_tree = ast.parse(current_source)
        except SyntaxError:
            self.last_error = "invalid Python"
            self._t(f"[feedback] dropped candidate: {self.last_error}")
            return None
        ok, reason = self._structure_preserved(current_tree, candidate_tree)
        if not ok:
            self.last_error = reason
            self._t(f"[feedback] dropped candidate: {self.last_error}")
            return None
        return source

    @staticmethod
    def _structure_preserved(current_tree: ast.AST, candidate_tree: ast.AST) -> tuple[bool, str]:
        current_defs = FeedbackPerturber._definition_signatures(current_tree)
        candidate_defs = FeedbackPerturber._definition_signatures(candidate_tree)
        if current_defs != candidate_defs:
            return False, "class/function definitions changed"
        current_calls = FeedbackPerturber._call_names(current_tree)
        candidate_calls = FeedbackPerturber._call_names(candidate_tree)
        if current_calls != candidate_calls:
            return False, "call structure changed"
        if not any(name.startswith("test") for _kind, name, _args in current_defs):
            return False, "current source has no test definition"
        return True, ""

    @staticmethod
    def _definition_signatures(tree: ast.AST) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
        out: list[tuple[str, str, tuple[str, ...]]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                out.append(("class", node.name, ()))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = tuple(arg.arg for arg in node.args.args)
                kind = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
                out.append((kind, node.name, args))
        return tuple(out)

    @staticmethod
    def _call_names(tree: ast.AST) -> tuple[str, ...]:
        return tuple(
            name
            for name in (FeedbackPerturber._call_name(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call))
            if name
        )

    @staticmethod
    def _call_name(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = FeedbackPerturber._call_name(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        return type(node).__name__


class FeedbackRunner:
    def __init__(
        self,
        *,
        config: PerturbationConfig,
        input_root: Path | str,
        output_root: Path | str,
        input_report: Path | str,
        iterations: int = 5,
        report_path: Path | str | None = None,
    ) -> None:
        self.config = config
        self.source = RepoLayout()
        self.input = OutputLayout(input_root)
        self.output = OutputLayout(output_root)
        self.input_report = Path(input_report)
        self.iterations = max(0, iterations)
        self.coverage = CoverageExtractor()
        self.report_path = Path(report_path) if report_path else None
        self._copied_rows: List[dict] = []
        self._feedback_results: List[FeedbackSourceResult] = []
        self._input_generated_count = 0
        self._needs_feedback_count = 0

    def _log(self, msg: str) -> None:
        if self.config.progress:
            print(msg, flush=True)

    def run(self) -> dict:
        report = json.loads(self.input_report.read_text(encoding="utf-8"))
        generated = [row for row in report.get("generated_instances", []) if row.get("model_passed_original") is True]
        copied = [row for row in generated if row.get("flipped_to_fail") is True]
        needs_feedback = [row for row in generated if row.get("flipped_to_fail") is False]
        self._input_generated_count = len(generated)
        self._needs_feedback_count = len(needs_feedback)

        self._log(
            "[feedback] loaded "
            f"{len(generated)} generated instance(s): "
            f"{len(copied)} existing flip(s), {len(needs_feedback)} non-flip(s)"
        )
        self._log(f"[feedback] copying existing flips to {self.output.root}")
        self._copied_rows = [self._copy_existing_flip(row) for row in copied]
        self._log(f"[feedback] copied {len(self._copied_rows)} existing flip(s)")
        self._write_report()

        repos = sorted({str(row.get("repo")) for row in needs_feedback if row.get("repo")})
        self._log(f"[feedback] running feedback over {len(repos)} repo(s)")
        for repo in repos:
            rows = [row for row in needs_feedback if row.get("repo") == repo]
            self._log(f"[feedback:{repo}] {len(rows)} source non-flip(s)")
            self._run_repo(repo, rows)
            self._write_report()

        return self._build_report()

    def _build_report(self) -> dict:
        attempts = [attempt for result in self._feedback_results for attempt in result.attempts]
        persisted_attempts = [attempt for attempt in attempts if attempt.persisted]
        retained_attempts = [attempt for attempt in attempts if attempt.kept is True]
        fallback_retained = [
            result for result in self._feedback_results
            if result.retained_source == "input_nonflip"
        ]
        successes = [result for result in self._feedback_results if result.succeeded]
        unresolved = [result for result in self._feedback_results if not result.succeeded]
        retained_rows = self._retained_output_rows()
        return {
            "summary": {
                "input_report": str(self.input_report),
                "input_root": str(self.input.root),
                "output_root": str(self.output.root),
                "generated_instances": len(retained_rows),
                "input_generated_instances": self._input_generated_count,
                "copied_existing_flips": len(self._copied_rows),
                "feedback_source_instances": self._needs_feedback_count,
                "feedback_iterations": self.iterations,
                "feedback_attempts": len(attempts),
                "feedback_instances_harvested": len(persisted_attempts),
                "feedback_instances_created": len(retained_attempts),
                "feedback_instances_retained": len(retained_attempts),
                "feedback_input_fallbacks_retained": len(fallback_retained),
                "feedback_total_retained": len(retained_attempts) + len(fallback_retained),
                "feedback_successful_flips": len(successes),
                "feedback_unsuccessful_sources": len(unresolved),
                "total_flips_in_output": len(self._copied_rows) + len(successes),
                "flipped_to_fail": sum(1 for row in retained_rows if row.get("flipped_to_fail") is True),
                "oracle_changed": sum(1 for row in retained_rows if row.get("oracle_changed") is True),
                "same_oracle": sum(1 for row in retained_rows if row.get("same_oracle") is True),
                "different_trace": sum(1 for row in retained_rows if row.get("trace_changed") is True),
                "same_trace": sum(1 for row in retained_rows if row.get("trace_same_as_original") is True),
            },
            "copied_existing_flips": self._copied_rows,
            "feedback_successes": [result.to_dict() for result in successes],
            "feedback_unresolved": [result.to_dict() for result in unresolved],
            "feedback_attempts": [attempt.to_dict() for attempt in attempts],
            "generated_instances": retained_rows,
        }

    def _retained_output_rows(self) -> List[dict]:
        rows: List[dict] = list(self._copied_rows)
        for result in self._feedback_results:
            for attempt in result.attempts:
                if attempt.kept is True:
                    rows.append(attempt.to_dict())
            if result.retained_source == "input_nonflip" and result.fallback_row:
                rows.append(result.fallback_row)
        return rows

    def _write_report(self) -> None:
        if self.report_path is None:
            return
        payload = self._build_report()
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.report_path.with_suffix(self.report_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.report_path)

    def _run_repo(self, repo: str, rows: List[dict]) -> None:
        self.config.repo = repo
        self.config.output_root = str(self.output.root)
        self.config.llm_perturb = False
        pipeline = PerturbationPipeline(self.config, source=self.source, output=self.output)
        perturber = FeedbackPerturber(
            LLMPerturbationConfig(
                provider=self.config.llm_provider or self.config.vendor,
                model=self.config.llm_model or self.config.model,
                n=1,
                temperature=self.config.llm_temperature,
            ),
            trace=None,
        )
        pipeline._setup_source_root()  # noqa: SLF001
        try:
            for idx, row in enumerate(rows, start=1):
                pipeline._log(
                    f"[feedback:{repo}] ({idx}/{len(rows)}) {row.get('new_id')} "
                    f"from {row.get('original_id')}"
                )
                result = FeedbackSourceResult(
                    repo=str(row["repo"]),
                    original_id=str(row["original_id"]),
                    start_new_id=str(row["new_id"]),
                    input_row=dict(row),
                )
                self._feedback_results.append(result)
                self._run_source_row(pipeline, perturber, row, result)
                self._write_report()
        finally:
            pipeline._teardown_source_root()  # noqa: SLF001

    def _run_source_row(
        self,
        pipeline: PerturbationPipeline,
        perturber: FeedbackPerturber,
        row: dict,
        result: FeedbackSourceResult,
    ) -> None:
        repo = str(row["repo"])
        original_id = str(row["original_id"])
        start_new_id = str(row["new_id"])

        original_ctx = pipeline._read_original_test(original_id)  # noqa: SLF001
        if original_ctx is None:
            return
        test_rel, original_source = original_ctx
        current_source = self._read_test_source(self.input, repo, start_new_id, test_rel)
        if current_source is None:
            return

        baseline = pipeline.baseline_coverage(original_id)
        trace_file, trace_funcs = pipeline._trace_targets(original_id)  # noqa: SLF001
        current_id = start_new_id
        current_layout = self.input
        current_row = row

        for iteration in range(self.iterations):
            current_source = self._read_test_source(current_layout, repo, current_id, test_rel)
            if current_source is None:
                pipeline._log(f"    i{iteration}: missing current source for {current_id}")
                break
            current_trace = self._trace_for(current_layout, repo, current_id)
            current_oracle = _oracle_answer(current_layout.oracle_path(repo, current_id))
            new_id = f"{start_new_id}__fb_i{iteration}"
            pipeline._log(f"    i{iteration}: proposing {new_id}")
            source = perturber.generate(
                original_source=original_source,
                current_source=current_source,
                test_rel_path=test_rel,
                trace_file=trace_file,
                trace_funcs=trace_funcs,
                repo_root=pipeline._source_root or self.source.repo_root,  # noqa: SLF001
                instance_dir=self.source.qa_instance_dir(repo, original_id),
                original_oracle=_oracle_answer(self.source.oracle_path(repo, original_id)),
                current_oracle=current_oracle,
                question=_question(self.source.oracle_path(repo, original_id)),
                question_kind=_question_kind(self.source.oracle_path(repo, original_id)),
                original_trace=baseline,
                current_trace=current_trace,
                same_trace=current_row.get("trace_same_as_original"),
                oracle_changed=current_row.get("oracle_changed"),
                original_model_result=str(current_row.get("model_results", {}).get(f"{self.config.model}_original", "pass")),
                current_model_result=str(current_row.get("model_results", {}).get(f"{self.config.model}_perturbed", "pass")),
            )
            if source is None:
                outcome = self._feedback_outcome(row, new_id, iteration)
                outcome.add_stage("feedback_generate", False, perturber.last_error or "no valid LLM source")
                result.attempts.append(outcome)
                pipeline._log(f"    i{iteration}: no valid LLM source ({perturber.last_error or 'unknown reason'})")
                self._write_report()
                continue

            outcome = self._run_candidate(pipeline, row, new_id, iteration, source, baseline)
            result.attempts.append(outcome)
            pipeline._log(
                "    "
                f"i{iteration}: saved={outcome.persisted} "
                f"flip={outcome.flipped_to_fail} "
                f"oracle_changed={outcome.oracle_changed} "
                f"trace_changed={outcome.trace_changed} "
                f"stage={self._last_stage_summary(outcome)}"
            )
            self._write_report()
            if outcome.flipped_to_fail:
                result.success_new_id = new_id
                pipeline._log(f"    i{iteration}: FLIP found, stopping this source")
                break
            if outcome.persisted:
                current_id = new_id
                current_layout = self.output
                current_row = outcome.to_dict()
            else:
                pipeline._log(f"    i{iteration}: candidate did not persist")
        self._retain_best_attempt(pipeline, row, result)
        self._write_report()
        return

    def _retain_best_attempt(self, pipeline: PerturbationPipeline, row: dict, result: FeedbackSourceResult) -> None:
        retained = self._best_attempt(result)
        result.retained_new_id = retained.new_id if retained else None
        result.retained_source = "feedback_attempt" if retained else None
        for attempt in result.attempts:
            if not attempt.persisted:
                continue
            if retained and attempt.new_id == retained.new_id:
                attempt.kept = True
                detail = "flip" if attempt.flipped_to_fail else "best non-flip"
                attempt.add_stage("retain", True, detail)
                pipeline._write_instance_metadata(attempt)  # noqa: SLF001
                continue
            pipeline._remove_output_instance(attempt.new_id)  # noqa: SLF001
            attempt.kept = False
            detail = (
                f"removed; retained {retained.new_id}"
                if retained else "removed; no retained feedback candidate"
            )
            attempt.add_stage("retain", False, detail)
        if retained:
            pipeline._log(f"    retained: {retained.new_id} flip={retained.flipped_to_fail}")
        else:
            copied = self._copy_input_instance(row)
            result.retained_new_id = str(row["new_id"])
            result.retained_source = "input_nonflip"
            result.fallback_row = copied
            pipeline._log(
                f"    retained fallback: {row['new_id']} "
                f"from input ({len(copied.get('copied_to_feedback_output', []))} artifact dir(s))"
            )

    def _best_attempt(self, result: FeedbackSourceResult) -> Optional[InstanceOutcome]:
        persisted = [attempt for attempt in result.attempts if attempt.persisted]
        if not persisted:
            return None
        flips = [attempt for attempt in persisted if attempt.flipped_to_fail]
        if flips:
            return flips[0]
        return max(persisted, key=self._nonflip_score)

    @staticmethod
    def _nonflip_score(outcome: InstanceOutcome) -> tuple:
        new_lines = outcome.new_lines_vs_baseline or 0
        new_edges = outcome.new_edges_vs_baseline or 0
        return (
            int(outcome.oracle_changed is True and outcome.trace_changed is True),
            int(outcome.oracle_changed is True),
            int(outcome.trace_changed is True),
            new_lines + new_edges,
            new_edges,
            new_lines,
            outcome.seed,
        )

    def _run_candidate(
        self,
        pipeline: PerturbationPipeline,
        row: dict,
        new_id: str,
        iteration: int,
        source: str,
        baseline: CoverageSignature,
    ) -> InstanceOutcome:
        outcome = self._feedback_outcome(row, new_id, iteration)
        outcome.add_stage("feedback_generate", True, "llm feedback source")
        materialized = pipeline._materialize_source(row["original_id"], new_id, source, outcome)  # noqa: SLF001
        if materialized is None:
            return outcome
        harvest = pipeline._harvest_step(row["original_id"], new_id, outcome)  # noqa: SLF001
        if harvest is None:
            return outcome
        sig = pipeline._record_trace_comparison(row["original_id"], harvest, outcome, baseline)  # noqa: SLF001
        outcome.add_stage(
            "feedback_trace",
            outcome.trace_changed is True,
            f"same_trace={outcome.trace_same_as_original} events={len(sig.events)}",
        )
        finalized = pipeline._finalize(new_id, outcome)  # noqa: SLF001
        if finalized.flipped_to_fail is None and _stage_ok(finalized, "evaluate"):
            finalized.add_stage("flip", False, "no flip")
        return finalized

    @staticmethod
    def _last_stage_summary(outcome: InstanceOutcome) -> str:
        if not outcome.stages:
            return "none"
        stage = outcome.stages[-1]
        status = "ok" if stage.ok else "failed"
        detail = (stage.detail or "").replace("\n", " ").strip()
        if len(detail) > 120:
            detail = detail[:117] + "..."
        return f"{stage.name}:{status}" + (f":{detail}" if detail else "")

    def _feedback_outcome(self, row: dict, new_id: str, iteration: int) -> InstanceOutcome:
        return InstanceOutcome(
            repo=str(row["repo"]),
            original_id=str(row["original_id"]),
            new_id=new_id,
            strategy="feedback_llm",
            seed=iteration,
            question_kind=row.get("question_kind"),
            model_passed_original=row.get("model_passed_original"),
            model=self.config.model,
            notes=f"feedback_from={row.get('new_id')} iteration={iteration}",
        )

    def _copy_existing_flip(self, row: dict) -> dict:
        out = self._copy_input_instance(row)
        out["copied_as"] = "existing_flip"
        return out

    def _copy_input_instance(self, row: dict) -> dict:
        repo = str(row["repo"])
        new_id = str(row["new_id"])
        copied_paths: List[str] = []
        for src, dst in (
            (self.input.qa_instance_dir(repo, new_id), self.output.qa_instance_dir(repo, new_id)),
            (self.input.eval_instance_dir(repo, new_id), self.output.eval_instance_dir(repo, new_id)),
            (
                self.input.prediction_dir(repo, new_id, self.config.vendor, self.config.model, self.config.tool),
                self.output.prediction_dir(repo, new_id, self.config.vendor, self.config.model, self.config.tool),
            ),
        ):
            if not src.exists():
                continue
            if dst.exists():
                if self.config.overwrite_existing:
                    shutil.rmtree(dst)
                else:
                    copied_paths.append(str(dst))
                    continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst)
            copied_paths.append(str(dst))
        out = dict(row)
        out["copied_to_feedback_output"] = copied_paths
        return out

    def _read_test_source(self, layout: OutputLayout | RepoLayout, repo: str, instance_id: str, test_rel: str) -> Optional[str]:
        path = layout.qa_instance_dir(repo, instance_id) / "files" / test_rel
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    def _trace_for(self, layout: OutputLayout | RepoLayout, repo: str, instance_id: str) -> Optional[CoverageSignature]:
        path = layout.qa_instance_dir(repo, instance_id) / "trace.log"
        if not path.exists() and isinstance(layout, RepoLayout):
            path = layout.harvest_artifacts_dir(repo, instance_id) / "trace.log"
        if not path.exists():
            return None
        return self.coverage.extract_file(path)


def run_feedback_from_report(
    *,
    base_config: PerturbationConfig,
    input_report: str,
    input_root: Optional[str],
    output_root: Optional[str],
    iterations: int,
    report_path: Optional[str] = None,
) -> dict:
    return FeedbackRunner(
        config=base_config,
        input_root=input_root or DEFAULT_OUTPUT_ROOT,
        output_root=output_root or Path("perturbation/generated_feedback"),
        input_report=input_report,
        iterations=iterations,
        report_path=report_path,
    ).run()
