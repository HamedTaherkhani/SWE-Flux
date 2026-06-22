"""Configuration objects for the perturbation pipeline.

Everything tunable lives here so behaviour is declarative and the orchestrator
stays thin. Sets of "structural" names protect shapes/dimensions/indices from
being perturbed -- changing those tends to break execution rather than make the
question *harder*, so we leave them alone by default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# Keyword arguments whose values describe *structure* (shapes, axes, sizes,
# dtypes, counts) rather than data. Perturbing them changes control flow / shapes
# instead of making the numeric reasoning harder, so they are protected.
DEFAULT_STRUCTURAL_KWARGS: frozenset[str] = frozenset(
    {
        "ndim", "ndmin", "axis", "axes", "size", "shape", "dtype", "order",
        "n", "k", "num", "repeats", "maxsize", "max_width", "width", "decimals",
        "seed", "random_state", "dims", "out", "keepdims", "kind",
    }
)

# Substrings/suffixes that mark a keyword (or dict-key) name as structural even
# when it is not in DEFAULT_STRUCTURAL_KWARGS verbatim (e.g. "input_shape",
# "expected_output_shape", "num_classes", "units", "n_features"). Matched
# case-insensitively against the name.
DEFAULT_STRUCTURAL_PATTERNS: tuple[str, ...] = (
    "shape", "ndim", "dim", "axis", "size", "units", "num", "count", "length",
    "len", "width", "height", "depth", "channels", "filters", "stride",
    "kernel", "padding", "dtype", "index", "idx", "seed",
)

# Calls whose *positional* arguments are structural (the leading args are shapes
# / ranges / dims). We leave their positional args untouched but still perturb
# their data-bearing keyword args.
DEFAULT_STRUCTURAL_CALLS: frozenset[str] = frozenset(
    {
        "range", "reshape", "zeros", "ones", "empty", "full", "eye", "identity",
        "arange", "linspace", "repeat", "tile", "broadcast_to", "expand_dims",
        "np.zeros", "np.ones", "np.empty", "np.full", "np.eye", "np.arange",
        "np.linspace", "np.reshape", "np.repeat", "np.tile",
        # Constrained constructors: their positional args must satisfy domain
        # rules (month in 1..12, etc.). Perturbing them raises exceptions and
        # breaks the harvest rather than producing a harder-but-valid input.
        "datetime", "date", "time", "timedelta",
        "DatetimeNoLeap", "DatetimeGregorian", "DatetimeProlepticGregorian",
        "DatetimeJulian", "DatetimeAllLeap", "Datetime360Day", "DatetimeJulianDay",
    }
)

# Substrings (case-insensitive) that mark a *call* name as a constrained
# constructor regardless of module prefix (e.g. ``cftime.DatetimeNoLeap``).
DEFAULT_STRUCTURAL_CALL_PATTERNS: tuple[str, ...] = ("datetime", "timedelta")


@dataclass
class PerturbationConfig:
    """Top-level configuration for a perturbation run."""

    # -- target model / dataset scope -----------------------------------------
    repo: str = "Keras"
    tool: str = "llm"
    vendor: str = "openai"
    model: str = "gpt-5.4-2026-03-05"

    # -- perturbation behaviour -----------------------------------------------
    strategies: List[str] = field(default_factory=lambda: ["boundary"])
    seeds: List[int] = field(default_factory=lambda: [7])
    magnitude: float = 1.0
    # Keep perturbed numeric vectors the same length as the original. Off would
    # let strategies resize vectors, which breaks shape-coupled code (e.g. an
    # array whose length must match another's axis -> broadcast errors).
    preserve_length: bool = True
    assertion_policy: str = "neutralize"  # "neutralize" | "keep"
    structural_kwargs: frozenset[str] = DEFAULT_STRUCTURAL_KWARGS
    structural_calls: frozenset[str] = DEFAULT_STRUCTURAL_CALLS
    structural_patterns: tuple[str, ...] = DEFAULT_STRUCTURAL_PATTERNS
    structural_call_patterns: tuple[str, ...] = DEFAULT_STRUCTURAL_CALL_PATTERNS

    # -- output / logging -----------------------------------------------------
    progress: bool = True  # print live progress while the pipeline runs

    # -- pipeline stages ------------------------------------------------------
    run_harvest: bool = True
    run_inference: bool = True
    run_eval: bool = True
    # Stop trying further (strategy, seed) candidates for an instance once one
    # of them flips the model from pass -> fail.
    stop_on_first_flip: bool = True
    overwrite_existing: bool = False

    # -- selection ------------------------------------------------------------
    only_passing: bool = True
    instance_ids: Optional[List[str]] = None  # explicit subset; None = all
    max_instances: Optional[int] = None

    # -- external tooling -----------------------------------------------------
    image: Optional[str] = None  # override IMAGE for run_qa_fromhost.sh
    harvest_timeout: int = 600
    inference_timeout: int = 3600
    inference_extra_args: List[str] = field(default_factory=list)
    # Interpreter for the LLM runner. The runner needs `aider-chat` (repo-map),
    # which lives in the project's `repo` conda env -- not necessarily the env
    # running this package. Set `inference_conda_env` to run it via `conda run`,
    # or `inference_python` to point at a specific interpreter directly.
    inference_python: Optional[str] = None
    inference_conda_env: Optional[str] = "repo"

    # -- coverage-guided exploration ------------------------------------------
    explore: bool = False
    explore_strategies: List[str] = field(
        default_factory=lambda: ["boundary", "threshold_straddle", "special_value"]
    )
    explore_seeds: List[int] = field(default_factory=lambda: list(range(8)))
    explore_budget: int = 12          # max harvest attempts per source instance
    explore_max_keep: int = 4         # max distinct kept candidates per instance
    explore_require_new_coverage: bool = True  # keep only if it hits new branches
    # Acceptance criterion for a harvested candidate:
    #   "coverage" -> keep if it reaches new branches (novelty search)
    #   "oracle"   -> keep if the harvested oracle_answer differs from the original
    accept_criterion: str = "coverage"
    explore_baseline: bool = True     # harvest the original once for a coverage baseline
    # Source for parsing the function under test for thresholds. By default the
    # repo's source is materialized from its eval image (via Docker) into
    # `snapshot_root` and removed afterwards; set `target_source_root` to use an
    # existing checkout instead, or `materialize_source=False` to use only the
    # test file's own literals.
    target_source_root: Optional[str] = None
    materialize_source: bool = True

    # -- LLM-based perturbation -----------------------------------------------
    # When enabled, an LLM proposes N structure-preserving perturbed test sources
    # per instance (reusing the repo read tools) instead of the AST strategies.
    llm_perturb: bool = False
    llm_n: int = 5
    llm_provider: Optional[str] = None   # defaults to `vendor`
    llm_model: Optional[str] = None      # defaults to `model`
    llm_temperature: float = 0.7
    llm_threads: int = 1                 # parallel OpenAI generation calls
    snapshot_root: Optional[str] = None
    cleanup_snapshot: bool = True

    # -- output location ------------------------------------------------------
    # Where generated (perturbed) instances + their evaluations are stored,
    # separate from the main benchmark. None -> perturbation/generated.
    output_root: Optional[str] = None

    # -- naming ---------------------------------------------------------------
    suffix_template: str = "__pert_{strategy}_s{seed}"

    def new_instance_id(self, original_id: str, strategy: str, seed: int) -> str:
        return original_id + self.suffix_template.format(strategy=strategy, seed=seed)

    def is_structural_name(self, name: Optional[str]) -> bool:
        """Whether a keyword/dict-key name denotes structure (so it's protected).

        Matches the explicit ``structural_kwargs`` set exactly, then falls back to
        case-insensitive substring matching against ``structural_patterns`` so
        names like ``input_shape`` or ``num_classes`` are caught too.
        """
        if not name:
            return False
        if name in self.structural_kwargs:
            return True
        lowered = name.lower()
        return any(pat in lowered for pat in self.structural_patterns)

    def is_structural_call(self, name: Optional[str]) -> bool:
        """Whether a call's *positional* args are structural (so left untouched).

        Matches the explicit ``structural_calls`` set (by full dotted name or by
        its tail component, so ``cftime.DatetimeNoLeap`` matches ``DatetimeNoLeap``)
        and the ``structural_call_patterns`` substrings (so any ``*datetime*``
        constructor is caught).
        """
        if not name:
            return False
        if name in self.structural_calls or name.split(".")[-1] in self.structural_calls:
            return True
        lowered = name.lower()
        return any(pat in lowered for pat in self.structural_call_patterns)
