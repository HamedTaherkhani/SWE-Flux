"""Coverage extraction from harvest traces.

``trace_plugin.py`` already records a line-level execution trace during harvest
(``trace.log``). We parse it into a coverage *signature* -- the set of executed
``(file, line)`` locations and consecutive-line *edges* within the traced
functions -- which the explorer uses as a fitness signal to steer perturbations
toward new branches/paths.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import FrozenSet, Optional, Tuple

# Matches lines emitted by trace_plugin._emit, e.g.:
#   2026-06-15 18:25:30.123 /testbed/keras/.../activations.py:123 keras...relu event=line ...
_TRACE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+\s+"
    r"(?P<path>[^:]+):(?P<line>\d+)\s+(?P<func>\S+)\s+event=(?P<event>\w+)"
)


def _normalize_path(path: str) -> str:
    """Drop container-specific prefixes so signatures compare across runs."""
    p = path.replace("\\", "/")
    marker = "/testbed/"
    idx = p.find(marker)
    return p[idx + len(marker):] if idx != -1 else p


Location = Tuple[str, int]
Edge = Tuple[str, int, int]


@dataclass(frozen=True)
class CoverageSignature:
    """A hashable summary of which lines/edges executed."""

    lines: FrozenSet[Location] = field(default_factory=frozenset)
    edges: FrozenSet[Edge] = field(default_factory=frozenset)

    def __bool__(self) -> bool:
        return bool(self.lines)

    def new_lines_vs(self, baseline: "CoverageSignature") -> FrozenSet[Location]:
        return frozenset(self.lines - baseline.lines)

    def new_edges_vs(self, baseline: "CoverageSignature") -> FrozenSet[Edge]:
        return frozenset(self.edges - baseline.edges)

    @property
    def key(self) -> int:
        """Stable hash of the line set (for novelty dedup)."""
        return hash(self.lines)


class CoverageExtractor:
    """Parses a ``trace.log`` into a :class:`CoverageSignature`."""

    def extract_text(self, text: str) -> CoverageSignature:
        lines: set[Location] = set()
        edges: set[Edge] = set()
        last_by_func: dict[str, int] = {}

        for raw in text.splitlines():
            m = _TRACE_RE.match(raw)
            if not m or m.group("event") not in ("line", "call", "return"):
                continue
            path = _normalize_path(m.group("path"))
            lineno = int(m.group("line"))
            func = m.group("func")
            lines.add((path, lineno))

            prev = last_by_func.get(func)
            if prev is not None and prev != lineno:
                edges.add((func, prev, lineno))
            last_by_func[func] = lineno

        return CoverageSignature(frozenset(lines), frozenset(edges))

    def extract_file(self, path: Path) -> Optional[CoverageSignature]:
        try:
            return self.extract_text(Path(path).read_text(encoding="utf-8", errors="replace"))
        except OSError:
            return None
