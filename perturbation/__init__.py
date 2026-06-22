"""Perturbation package: generate harder QA instances from passing ones.

Pipeline: select passing instances -> perturb test inputs (AST, no LLM) ->
re-harvest a fresh oracle -> rebuild the eval question -> run inference ->
score, to see whether the perturbation flips the model from pass to fail.

The high-level entrypoint is :class:`~perturbation.pipeline.PerturbationPipeline`.
"""

from .config import PerturbationConfig
from .models import InstanceOutcome, PassFailReport
from .paths import RepoLayout
from .perturber import TestPerturber
from .pipeline import PerturbationPipeline

__all__ = [
    "PerturbationConfig",
    "InstanceOutcome",
    "PassFailReport",
    "RepoLayout",
    "TestPerturber",
    "PerturbationPipeline",
]
