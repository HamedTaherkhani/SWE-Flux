"""Orchestrates the full perturbation -> harvest -> infer -> evaluate loop.

Two modes:

* one-shot (default): for each *passing* instance, try (strategy, seed) candidates
  until one produces a valid harder instance (and optionally one that flips the
  model to failing).
* explore (``config.explore``): coverage-guided search that keeps multiple
  perturbations per instance, each reaching new branches (see ``explorer.py``).

Each stage is isolated behind an adapter, and the per-attempt work is broken into
small steps (`_materialize_perturb`, `_harvest_step`, `_finalize`) so both modes
reuse the same building blocks.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from .analysis import TargetAnalyzer
from .config import PerturbationConfig
from .coverage import CoverageExtractor, CoverageSignature
from .dataset import EvalDatasetBuilder
from .harvest import HarvestResult, OracleHarvester
from .inference import InferenceRunner
from .materializer import InstanceMaterializer, MaterializedInstance
from .models import InstanceOutcome, PassFailReport
from .paths import DEFAULT_OUTPUT_ROOT, OutputLayout, RepoLayout, ensure_repo_on_path
from .perturber import TestPerturber
from .selection import InstanceClassifier
from .snapshot import RepoSnapshotManager

ensure_repo_on_path()
from evaluation_scripts import evaluate_qa_answers as eqa  # noqa: E402


class PerturbationPipeline:
    def __init__(
        self,
        config: PerturbationConfig,
        source: Optional[RepoLayout] = None,
        output: Optional[OutputLayout] = None,
    ) -> None:
        self.config = config
        # source = the real checkout (originals + harvesting/inference tooling)
        self.source = source or RepoLayout()
        # output = self-contained home for generated artifacts
        self.output = output or OutputLayout(config.output_root or DEFAULT_OUTPUT_ROOT)

        self.source_classifier = InstanceClassifier(config, self.source)
        self.output_classifier = InstanceClassifier(config, self.output)
        self.perturber = TestPerturber(config)
        # materialize + harvest happen in the source tree (harvest requires it)
        self.materializer = InstanceMaterializer(config, self.source)
        self.harvester = OracleHarvester(config, self.source)
        # dataset + predictions live in the output tree
        self.dataset = EvalDatasetBuilder(config, self.output)
        self.inference = InferenceRunner(config, self.source, self.output)
        # repo source snapshot (for parsing the function under test for thresholds)
        self.snapshots = RepoSnapshotManager(config, self.source)
        self._source_root: Optional[Path] = None   # effective source root, if any
        self._materialized = False                  # did we create the snapshot?
        self._threshold_cache: dict[str, Tuple[float, ...]] = {}
        self._baseline_cache: dict[str, CoverageSignature] = {}
        self._coverage_extractor = CoverageExtractor()

    def _log(self, msg: str) -> None:
        """Print live progress (flushed) when enabled."""
        if self.config.progress:
            print(msg, flush=True)

    # -- selection -------------------------------------------------------------
    def select_targets(self) -> Tuple[PassFailReport, List[str]]:
        report = self.source_classifier.classify_repo(self.config.repo, self.config.instance_ids)
        targets = report.passing_ids if self.config.only_passing else [
            c.instance_id for c in report.classifications
        ]
        targets = self._sample_targets_by_question_kind(targets)
        if self.config.max_per_repo is not None:
            targets = targets[: max(0, self.config.max_per_repo)]
        if self.config.max_instances is not None:
            targets = targets[: self.config.max_instances]
        return report, targets

    def _question_kind(self, instance_id: str) -> str:
        try:
            data = eqa.load_json(self.source.oracle_path(self.config.repo, instance_id))
        except Exception:  # noqa: BLE001
            return "UNKNOWN"
        if isinstance(data, dict):
            return str(data.get("question_kind") or "UNKNOWN")
        return "UNKNOWN"

    def _sample_targets_by_question_kind(self, targets: List[str]) -> List[str]:
        n = self.config.sample_per_category
        if n is None:
            return targets
        if n <= 0:
            return []

        counts: dict[str, int] = {}
        sampled: List[str] = []
        for instance_id in targets:
            kind = self._question_kind(instance_id)
            if counts.get(kind, 0) >= n:
                continue
            counts[kind] = counts.get(kind, 0) + 1
            sampled.append(instance_id)
        if self.config.progress:
            detail = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
            self._log(f"[{self.config.repo}] selected by question_kind: {detail}")
        return sampled

    def _candidates(self) -> Iterator[Tuple[str, int]]:
        for strategy in self.config.strategies:
            for seed in self.config.seeds:
                yield strategy, seed

    # -- reusable steps --------------------------------------------------------
    def _materialize_perturb(
        self, original_id: str, new_id: str, strategy: str, seed: int, outcome: InstanceOutcome
    ) -> Optional[MaterializedInstance]:
        repo = self.config.repo
        try:
            materialized = self.materializer.materialize(repo, original_id, new_id)
        except Exception as exc:  # noqa: BLE001
            outcome.add_stage("materialize", False, str(exc))
            return None
        outcome.add_stage("materialize", True)

        # Feed the strategy thresholds parsed from the function under test (if a
        # source root is available), in addition to the test's own literals.
        self.perturber._extra_thresholds = self._extra_thresholds_for(original_id)  # noqa: SLF001
        result = self.perturber.perturb(materialized.original_source, strategy_name=strategy, seed=seed)
        outcome.n_changes = result.n_changes
        if result.n_changes == 0:
            outcome.add_stage("perturb", False, "no eligible literals changed")
            self.materializer.remove(repo, new_id)
            return None
        self.materializer.write_perturbed_source(materialized, result.new_source)
        outcome.add_stage("perturb", True, f"{result.n_changes} literals")
        return materialized

    def _materialize_source(
        self, original_id: str, new_id: str, source: str, outcome: InstanceOutcome
    ) -> Optional[MaterializedInstance]:
        """Materialize a sibling instance and write a pre-made perturbed source
        (used for LLM-proposed variants)."""
        repo = self.config.repo
        try:
            materialized = self.materializer.materialize(repo, original_id, new_id)
        except Exception as exc:  # noqa: BLE001
            outcome.add_stage("materialize", False, str(exc))
            return None
        outcome.add_stage("materialize", True)

        if source.strip() == materialized.original_source.strip():
            outcome.add_stage("perturb", False, "no change vs original")
            self.materializer.remove(repo, new_id)
            return None
        changed = sum(
            1 for a, b in zip(source.splitlines(), materialized.original_source.splitlines()) if a != b
        )
        outcome.n_changes = max(1, changed)
        self.materializer.write_perturbed_source(materialized, source)
        outcome.add_stage("perturb", True, f"llm variant (~{outcome.n_changes} lines changed)")
        return materialized

    def _read_original_test(self, original_id: str) -> Optional[Tuple[str, str]]:
        """Return (test_rel_path, original_source) for an instance, or None."""
        repo = self.config.repo
        eval_sh = self.source.eval_script(repo, original_id)
        try:
            test_rel = self.materializer._test_rel_path(eval_sh.read_text(encoding="utf-8"))  # noqa: SLF001
        except Exception:  # noqa: BLE001
            return None
        test_file = self.source.qa_instance_dir(repo, original_id) / "files" / test_rel
        if not test_file.exists():
            return None
        return test_rel, test_file.read_text(encoding="utf-8")

    def _harvest_step(self, original_id: str, new_id: str, outcome: InstanceOutcome) -> Optional[HarvestResult]:
        """Harvest a fresh oracle. Leaves the instance in the source tree (with
        its trace.log) so coverage can be read before relocation."""
        repo = self.config.repo
        if not self.config.run_harvest:
            outcome.add_stage("harvest", False, "skipped (run_harvest=False)")
            self.materializer.remove(repo, new_id)
            return None
        harvest = self.harvester.harvest(repo, new_id)
        outcome.add_stage("harvest", harvest.ok, harvest.detail)
        if not harvest.ok:
            self.materializer.remove(repo, new_id)
            return None
        outcome.oracle_changed = self._oracle_changed(original_id, new_id)
        return harvest

    def _finalize(self, new_id: str, outcome: InstanceOutcome) -> InstanceOutcome:
        """Relocate to output, build the eval entry, run inference + scoring."""
        repo = self.config.repo
        try:
            self.materializer.relocate(repo, new_id, self.output)
            outcome.add_stage("relocate", True, str(self.output.qa_instance_dir(repo, new_id)))
        except Exception as exc:  # noqa: BLE001
            outcome.add_stage("relocate", False, str(exc))
            return outcome

        try:
            self.dataset.build(repo, new_id)
            outcome.add_stage("dataset", True)
        except Exception as exc:  # noqa: BLE001
            outcome.add_stage("dataset", False, str(exc))
            self._write_instance_metadata(outcome)
            return outcome

        if not self.config.run_inference:
            outcome.add_stage("inference", False, "skipped (run_inference=False)")
            self._write_instance_metadata(outcome)
            return outcome
        inf = self.inference.run(repo, new_id)
        outcome.add_stage("inference", inf.ok, inf.detail)
        if not inf.ok:
            self._write_instance_metadata(outcome)
            return outcome

        if not self.config.run_eval:
            outcome.add_stage("evaluate", False, "skipped (run_eval=False)")
            self._write_instance_metadata(outcome)
            return outcome
        classification = self.output_classifier.classify_instance(repo, new_id)
        outcome.model_passed_new = classification.passing
        outcome.add_stage("evaluate", True, classification.reason)
        if outcome.flipped_to_fail is not None:
            outcome.add_stage(
                "flip",
                outcome.flipped_to_fail,
                "pass->fail" if outcome.flipped_to_fail else "no flip",
            )
        self._write_instance_metadata(outcome)
        return outcome

    # -- one-shot per-instance attempt ----------------------------------------
    def _attempt(self, original_id: str, strategy: str, seed: int, original_passed: bool) -> InstanceOutcome:
        repo = self.config.repo
        new_id = self.config.new_instance_id(original_id, strategy, seed)
        outcome = InstanceOutcome(
            repo=repo, original_id=original_id, new_id=new_id,
            strategy=strategy, seed=seed, model_passed_original=original_passed,
            model=self.config.model, question_kind=self._question_kind(original_id),
        )

        materialized = self._materialize_perturb(original_id, new_id, strategy, seed, outcome)
        if materialized is None:
            return outcome
        harvest = self._harvest_step(original_id, new_id, outcome)
        if harvest is None:
            return outcome
        self._record_trace_comparison(original_id, harvest, outcome)
        return self._finalize(new_id, outcome)

    def _remove_output_instance(self, new_id: str) -> None:
        """Delete a finalized instance from the output tree (used to roll back a
        candidate that did not satisfy the flip gate after inference)."""
        import shutil
        repo = self.config.repo
        for path in (
            self.output.qa_instance_dir(repo, new_id),
            self.output.eval_instance_dir(repo, new_id),
            self.output.prediction_dir(repo, new_id, self.config.vendor, self.config.model, self.config.tool),
        ):
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)

    def _oracle_changed(self, original_id: str, new_id: str) -> Optional[bool]:
        """Compare the original oracle (source) with the freshly harvested one.

        Called right after harvest, before relocation, so the new oracle is still
        in the source tree.
        """
        try:
            orig = eqa.load_json(self.source.oracle_path(self.config.repo, original_id))
            new = eqa.load_json(self.source.oracle_path(self.config.repo, new_id))
        except Exception:  # noqa: BLE001
            return None
        return orig.get("oracle_answer") != new.get("oracle_answer")

    def baseline_coverage(self, original_id: str) -> CoverageSignature:
        """Harvest a throwaway original copy once and cache its trace signature."""
        if original_id in self._baseline_cache:
            return self._baseline_cache[original_id]
        if not (self.config.explore_baseline and self.config.run_harvest):
            self._baseline_cache[original_id] = CoverageSignature()
            return self._baseline_cache[original_id]

        repo = self.config.repo
        tmp_id = f"{original_id}__baseline_tmp"
        try:
            self.materializer.remove(repo, tmp_id)
            self.materializer.materialize(repo, original_id, tmp_id)
            harvest = self.harvester.harvest(repo, tmp_id)
            if harvest.ok and harvest.trace_path:
                sig = self._coverage_extractor.extract_file(harvest.trace_path) or CoverageSignature()
            else:
                sig = CoverageSignature()
        except Exception:  # noqa: BLE001
            sig = CoverageSignature()
        finally:
            self.materializer.remove(repo, tmp_id)

        self._baseline_cache[original_id] = sig
        return sig

    def _record_trace_comparison(
        self,
        original_id: str,
        harvest: HarvestResult,
        outcome: InstanceOutcome,
        baseline: Optional[CoverageSignature] = None,
    ) -> CoverageSignature:
        """Populate trace/coverage comparison fields for a harvested candidate."""
        sig = (
            self._coverage_extractor.extract_file(harvest.trace_path)
            if harvest.trace_path else None
        ) or CoverageSignature()
        baseline = baseline if baseline is not None else self.baseline_coverage(original_id)

        outcome.covered_lines = len(sig.lines)
        outcome.new_lines_vs_baseline = len(sig.new_lines_vs(baseline))
        outcome.new_edges_vs_baseline = len(sig.new_edges_vs(baseline))
        outcome.trace_same_as_original = (
            sig.events == baseline.events
            if sig and baseline else None
        )
        return sig

    def _write_instance_metadata(self, outcome: InstanceOutcome) -> None:
        """Write a per-generated-instance JSON report next to its oracle."""
        if not outcome.harvested:
            return
        path = self.output.qa_instance_dir(outcome.repo, outcome.new_id) / "perturbation_result.json"
        if not path.parent.exists():
            return
        try:
            path.write_text(json.dumps(outcome.to_dict(), indent=2) + "\n", encoding="utf-8")
        except OSError:
            return

    # -- source thresholds (function under test) -------------------------------
    def _trace_targets(self, original_id: str) -> Tuple[str, List[str]]:
        """Parse TRACE_FILE / TRACE_FUNC out of the instance's eval.sh."""
        eval_sh = self.source.eval_script(self.config.repo, original_id)
        trace_file, funcs = "", []
        vars_seen: dict[str, str] = {}
        try:
            for line in eval_sh.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                exported = line.startswith("export ")
                expr = line[len("export "):] if exported else line
                name, raw_value = expr.split("=", 1)
                name = name.strip()
                value = raw_value.strip().strip('"').strip("'")
                if value.startswith("$"):
                    value = vars_seen.get(value[1:], value)
                vars_seen[name] = value
                if exported and name == "TRACE_FILE":
                    trace_file = value
                elif exported and name == "TRACE_FUNC":
                    raw = value
                    funcs = [f for f in raw.split(",") if f]
        except OSError:
            pass
        if not trace_file and not funcs:
            funcs = self._trace_targets_from_question(original_id)
        return trace_file, funcs

    def _trace_targets_from_question(self, original_id: str) -> List[str]:
        """Fallback for instances whose eval.sh lacks trace exports.

        Some repos encode the target dynamic extent only in the oracle question
        text. Extract dotted Python targets from backticked spans so the LLM
        perturbation prompt still gives the read tools useful source hints.
        """
        try:
            data = eqa.load_json(self.source.oracle_path(self.config.repo, original_id))
        except Exception:  # noqa: BLE001
            return []
        question = str(data.get("question", "")) if isinstance(data, dict) else ""
        out: List[str] = []
        for span in re.findall(r"`([^`]+)`", question):
            for match in re.findall(r"\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*){2,}\b", span):
                if match not in out:
                    out.append(match)
        return out

    def _extra_thresholds_for(self, original_id: str) -> Tuple[float, ...]:
        """Thresholds from the function under test, via the source snapshot."""
        if self._source_root is None:
            return ()
        if original_id in self._threshold_cache:
            return self._threshold_cache[original_id]

        trace_file, funcs = self._trace_targets(original_id)
        vals: set[float] = set()
        if trace_file:
            vals |= set(TargetAnalyzer.from_target_source(self._source_root / trace_file, funcs).thresholds)
        elif funcs:
            vals |= set(TargetAnalyzer.from_dotted_targets(self._source_root, funcs).thresholds)

        result = tuple(sorted(vals))
        self._threshold_cache[original_id] = result
        return result

    def _setup_source_root(self) -> None:
        """Resolve the source root: explicit path, else a materialized snapshot."""
        if self.config.target_source_root:
            self._source_root = Path(self.config.target_source_root).resolve()
            return
        if self.config.materialize_source:
            dest = self.snapshots.materialize(self.config.repo)
            if dest is not None:
                self._source_root = dest
                self._materialized = True

    def _teardown_source_root(self) -> None:
        if self._materialized and self.config.cleanup_snapshot:
            self.snapshots.cleanup(self.config.repo)
        self._source_root = None
        self._materialized = False

    # -- top-level run ---------------------------------------------------------
    def run(self) -> List[InstanceOutcome]:
        if self.config.accept_criterion == "flip" and not (self.config.run_inference and self.config.run_eval):
            self._log(
                "[warn] --accept-on is deprecated as a retention gate; flip status "
                "will be reported as unknown when inference/eval are disabled."
            )
        self._setup_source_root()
        try:
            if self.config.llm_perturb:
                return self._run_llm()
            if self.config.explore:
                return self._run_explore()
            return self._run_one_shot()
        finally:
            self._teardown_source_root()

    def _run_one_shot(self) -> List[InstanceOutcome]:
        report, targets = self.select_targets()
        passing = set(report.passing_ids)
        total = len(targets)
        self._log(f"[{self.config.repo}] one-shot over {total} instance(s)")
        outcomes: List[InstanceOutcome] = []

        for idx, original_id in enumerate(targets, start=1):
            original_passed = original_id in passing
            self._log(f"[{self.config.repo}] ({idx}/{total}) {original_id}")
            for strategy, seed in self._candidates():
                outcome = self._attempt(original_id, strategy, seed, original_passed)
                outcomes.append(outcome)
                self._log("    " + self._fmt_outcome(outcome))
                if self.config.stop_on_first_flip and outcome.flipped_to_fail:
                    break
        return outcomes

    def _run_llm(self) -> List[InstanceOutcome]:
        """LLM proposes N structure-preserving variants per instance; each is
        harvested and gated like an AST candidate (reusing the explorer).

        The LLM generation calls (independent OpenAI conversations) run in a
        thread pool (``llm_threads``); harvesting then proceeds serially because
        ``run_qa_fromhost.sh`` uses a single shared container name.
        """
        from concurrent.futures import ThreadPoolExecutor
        from .coverage import CoverageSignature
        from .explorer import CoverageGuidedExplorer  # local import to avoid cycle
        from .llm_strategy import LLMPerturber, LLMPerturbationConfig

        report, targets = self.select_targets()
        passing = set(report.passing_ids)
        total = len(targets)
        threads = max(1, self.config.llm_threads)
        self._log(
            f"[{self.config.repo}] llm-perturb over {total} instance(s), "
            f"n={self.config.llm_n}, llm_threads={threads}"
        )

        perturber = LLMPerturber(
            LLMPerturbationConfig(
                provider=self.config.llm_provider or self.config.vendor,
                model=self.config.llm_model or self.config.model,
                n=self.config.llm_n,
                temperature=self.config.llm_temperature,
            ),
            trace=self._log if threads == 1 else None,  # avoid interleaved trace spam
        )
        explorer = CoverageGuidedExplorer(self)
        repo = self.config.repo

        # -- Phase 1: generate variants for all instances (parallel OpenAI calls)
        def _generate(original_id: str) -> Tuple[str, List[str]]:
            ctx = self._read_original_test(original_id)
            if ctx is None:
                return original_id, []
            test_rel, source = ctx
            trace_file, trace_funcs = self._trace_targets(original_id)
            variants = perturber.generate_variants(
                original_source=source,
                test_rel_path=test_rel,
                trace_file=trace_file,
                trace_funcs=trace_funcs,
                repo_root=self._source_root or self.source.repo_root,
                instance_dir=self.source.qa_instance_dir(repo, original_id),
                n=self.config.llm_n,
            )
            return original_id, variants

        self._log(f"[{repo}] generating variants ({threads} thread(s))...")
        variants_by_id: dict[str, List[str]] = {}
        if threads == 1:
            for oid in targets:
                variants_by_id[oid] = _generate(oid)[1]
        else:
            with ThreadPoolExecutor(max_workers=threads) as pool:
                for oid, variants in pool.map(_generate, targets):
                    variants_by_id[oid] = variants
        self._log(f"[{repo}] variants ready: {sum(len(v) for v in variants_by_id.values())} total")

        # -- Phase 2: harvest + gate + score each variant (serial; Docker-bound)
        outcomes: List[InstanceOutcome] = []
        for idx, original_id in enumerate(targets, start=1):
            variants = variants_by_id.get(original_id, [])
            self._log(f"[{repo}] ({idx}/{total}) {original_id}: {len(variants)} variant(s)")
            if not variants:
                continue

            baseline = explorer._baseline_coverage(original_id)  # noqa: SLF001
            seen: set = set()
            for i, src in enumerate(variants):
                outcome = explorer._one(  # noqa: SLF001
                    original_id, "llm", i, original_id in passing, baseline, seen, source=src
                )
                outcomes.append(outcome)
                self._log("    " + self._fmt_outcome(outcome))
        return outcomes

    def _run_explore(self) -> List[InstanceOutcome]:
        from .explorer import CoverageGuidedExplorer  # local import to avoid cycle

        report, targets = self.select_targets()
        passing = set(report.passing_ids)
        total = len(targets)
        self._log(f"[{self.config.repo}] explore over {total} instance(s)")
        explorer = CoverageGuidedExplorer(self)
        outcomes: List[InstanceOutcome] = []
        for idx, original_id in enumerate(targets, start=1):
            self._log(f"[{self.config.repo}] ({idx}/{total}) {original_id}")
            outcomes.extend(explorer.explore(original_id, original_id in passing))
        return outcomes

    @staticmethod
    def _fmt_outcome(o: InstanceOutcome) -> str:
        """One-line progress description of an attempt."""
        last = o.stages[-1] if o.stages else None
        stage = f"{last.name}={'ok' if last.ok else (last.detail or 'fail')[:48]}" if last else "no-stage"
        flip = {True: "FLIP->FAIL", False: "still-pass", None: ""}[o.flipped_to_fail]
        cov = f" cov+{o.new_lines_vs_baseline}L" if o.new_lines_vs_baseline is not None else ""
        keep = "" if o.kept is None else ("save " if o.kept else "drop ")
        return f"{keep}{o.strategy}/s{o.seed} changes={o.n_changes}{cov} [{stage}] {flip}".rstrip()
