#!/usr/bin/env python3
"""Run read-only repository QA evaluation using LLM tool-calling + aider RepoMap.

Host mode (default):
- Starts one docker container per selected repository image.
- Copies qa_instances_eval/<repo> into /testbed/qa_instances_eval/<repo>.
- Runs this script inside the container in worker mode.
- Copies output answers back to host:
  <output-root>/llm/<provider>/<model>/<repo>/<instance>/answer.json

Worker mode (--worker):
- Reads each instance question.json.
- Uses read-only tools (get_repo_map, list_dir, read_file).
- Uses aider.repomap.RepoMap for repository structure/context.
- Calls the selected provider model and writes answer.json per instance.
"""

from __future__ import annotations

import argparse
import datetime as dt
import inspect
import json
import math
import os
import re
import shlex
import subprocess
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent


# ---------------------------
# Shared helpers
# ---------------------------


def sanitize_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s.strip())


def run_checked(cmd: Sequence[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        check=True,
        text=True,
        capture_output=capture,
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def select_instances(repo_instances_dir: Path, num_instances: str) -> List[str]:
    qfiles = sorted(repo_instances_dir.glob("*/question.json"))
    instance_ids = [p.parent.name for p in qfiles]
    if num_instances == "all":
        return instance_ids
    limit = int(num_instances)
    return instance_ids[: max(0, min(limit, len(instance_ids)))]


USAGE_NUMERIC_KEYS = [
    "requests",
    "usage_missing_requests",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cached_input_tokens",
    "reasoning_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
]

MODEL_COSTS_PATH = REPO_ROOT / "evaluations" / "llm" / "provider_model_costs.json"
_MODEL_COSTS_CACHE: Optional[Dict[str, Any]] = None


def _to_int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except Exception:
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return int(float(s))
        except Exception:
            return None
    return None


def _to_float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return float(s)
        except Exception:
            return None
    return None


def empty_usage(provider: str, model: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"provider": provider, "model": model}
    for key in USAGE_NUMERIC_KEYS:
        payload[key] = 0
    return payload


def merge_usage(into: Dict[str, Any], usage: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(usage, dict):
        return into
    for key in USAGE_NUMERIC_KEYS:
        inc = _to_int_or_none(usage.get(key))
        if inc is None:
            continue
        into[key] = int(into.get(key, 0)) + max(0, inc)
    if int(into.get("total_tokens", 0)) <= 0:
        into["total_tokens"] = int(into.get("input_tokens", 0)) + int(into.get("output_tokens", 0))
    return into


def _compute_usage_cost_with_rates(
    *,
    usage: Dict[str, Any],
    input_cost_per_1m: Optional[float],
    output_cost_per_1m: Optional[float],
    cached_input_cost_per_1m: Optional[float],
) -> Dict[str, Any]:
    in_rate = _to_float_or_none(input_cost_per_1m)
    out_rate = _to_float_or_none(output_cost_per_1m)
    cache_rate = _to_float_or_none(cached_input_cost_per_1m)

    pricing = {
        "input_cost_per_1m": in_rate,
        "output_cost_per_1m": out_rate,
        "cached_input_cost_per_1m": cache_rate if cache_rate is not None else in_rate,
    }

    if in_rate is None or out_rate is None:
        return {
            "configured": False,
            "currency": "USD",
            "pricing": pricing,
            "cost_usd": None,
        }

    input_tokens = max(0, int(_to_int_or_none(usage.get("input_tokens")) or 0))
    output_tokens = max(0, int(_to_int_or_none(usage.get("output_tokens")) or 0))
    cached_input_tokens = max(0, int(_to_int_or_none(usage.get("cached_input_tokens")) or 0))
    cached_input_tokens = min(cached_input_tokens, input_tokens)
    uncached_input_tokens = max(0, input_tokens - cached_input_tokens)
    eff_cache_rate = in_rate if cache_rate is None else cache_rate

    input_cost = (uncached_input_tokens / 1_000_000.0) * in_rate
    cached_input_cost = (cached_input_tokens / 1_000_000.0) * eff_cache_rate
    output_cost = (output_tokens / 1_000_000.0) * out_rate
    total_cost = input_cost + cached_input_cost + output_cost

    return {
        "configured": True,
        "currency": "USD",
        "pricing": pricing,
        "billable_tokens": {
            "input_uncached": uncached_input_tokens,
            "input_cached": cached_input_tokens,
            "output": output_tokens,
        },
        "cost_breakdown_usd": {
            "input_uncached": input_cost,
            "input_cached": cached_input_cost,
            "output": output_cost,
        },
        "cost_usd": total_cost,
    }


def _model_candidates(model: str) -> List[str]:
    raw = (model or "").strip()
    if not raw:
        return []
    out: List[str] = [raw]

    # Common version/date suffixes, e.g. gpt-5.4-2026-03-05.
    m = re.match(r"^(.*)-\d{4}-\d{2}-\d{2}$", raw)
    if m:
        out.append(m.group(1))
    m2 = re.match(r"^(.*)-\d{8}$", raw)
    if m2:
        out.append(m2.group(1))

    # Common stability tags.
    if raw.endswith("-latest"):
        out.append(raw[: -len("-latest")])
    if raw.endswith("-preview"):
        out.append(raw[: -len("-preview")])

    # Deduplicate, preserve order.
    dedup: List[str] = []
    seen = set()
    for c in out:
        if c and c not in seen:
            dedup.append(c)
            seen.add(c)
    return dedup


def load_model_costs_db() -> Dict[str, Any]:
    global _MODEL_COSTS_CACHE
    if _MODEL_COSTS_CACHE is not None:
        return _MODEL_COSTS_CACHE
    if not MODEL_COSTS_PATH.exists():
        _MODEL_COSTS_CACHE = {}
        return _MODEL_COSTS_CACHE
    try:
        payload = load_json(MODEL_COSTS_PATH)
    except Exception:
        payload = {}
    _MODEL_COSTS_CACHE = payload if isinstance(payload, dict) else {}
    return _MODEL_COSTS_CACHE


def resolve_model_cost_entry(provider: str, model: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    db = load_model_costs_db()
    provider_obj = db.get(provider, {})
    if not isinstance(provider_obj, dict):
        return None, {
            "provider": provider,
            "model": model,
            "pricing_file": str(MODEL_COSTS_PATH),
            "matched": False,
            "reason": f"provider '{provider}' not found in pricing file",
        }

    model_table = provider_obj.get("models", provider_obj)
    if not isinstance(model_table, dict):
        return None, {
            "provider": provider,
            "model": model,
            "pricing_file": str(MODEL_COSTS_PATH),
            "matched": False,
            "reason": f"provider '{provider}' has invalid model table in pricing file",
        }

    aliases = provider_obj.get("aliases", {})
    if not isinstance(aliases, dict):
        aliases = {}

    candidates = _model_candidates(model)
    for cand in candidates:
        if cand in aliases:
            alias_target = str(aliases[cand])
            entry = model_table.get(alias_target)
            if isinstance(entry, dict):
                return dict(entry), {
                    "provider": provider,
                    "model": model,
                    "matched": True,
                    "matched_model": alias_target,
                    "match_type": "alias",
                    "pricing_file": str(MODEL_COSTS_PATH),
                }

    for cand in candidates:
        entry = model_table.get(cand)
        if isinstance(entry, dict):
            return dict(entry), {
                "provider": provider,
                "model": model,
                "matched": True,
                "matched_model": cand,
                "match_type": "exact",
                "pricing_file": str(MODEL_COSTS_PATH),
            }

    # Prefix fallback (supports versioned model ids that share a base name).
    keys = sorted([str(k) for k in model_table.keys()], key=len, reverse=True)
    for cand in candidates:
        for key in keys:
            if cand.startswith(key):
                entry = model_table.get(key)
                if isinstance(entry, dict):
                    return dict(entry), {
                        "provider": provider,
                        "model": model,
                        "matched": True,
                        "matched_model": key,
                        "match_type": "prefix",
                        "pricing_file": str(MODEL_COSTS_PATH),
                    }

    return None, {
        "provider": provider,
        "model": model,
        "matched": False,
        "match_type": "none",
        "pricing_file": str(MODEL_COSTS_PATH),
        "reason": f"model entry not found in cost json for provider='{provider}', model='{model}'",
    }


def compute_usage_cost_for_model(*, provider: str, model: str, usage: Dict[str, Any]) -> Dict[str, Any]:
    entry, lookup = resolve_model_cost_entry(provider, model)
    if entry is None:
        return {
            "configured": False,
            "currency": "USD",
            "cost_usd": None,
            "model_lookup": lookup,
            "reason": str(lookup.get("reason", "model entry not found in cost json")),
        }

    cost = _compute_usage_cost_with_rates(
        usage=usage,
        input_cost_per_1m=_to_float_or_none(entry.get("input_cost_per_1m")),
        output_cost_per_1m=_to_float_or_none(entry.get("output_cost_per_1m")),
        cached_input_cost_per_1m=_to_float_or_none(entry.get("cached_input_cost_per_1m")),
    )
    cost["model_lookup"] = lookup
    cost["pricing_file"] = str(MODEL_COSTS_PATH)
    return cost


def write_repo_usage_file(repo_out_root: Path, provider: str, model: str) -> None:
    repo_out_root = repo_out_root.resolve()
    all_usage = empty_usage(provider, model)
    instances: List[Dict[str, Any]] = []
    total_cost = 0.0
    has_unknown_cost = False

    for inst_dir in sorted(p for p in repo_out_root.iterdir() if p.is_dir()):
        usage_path = inst_dir / "usage.json"
        if not usage_path.exists():
            continue
        try:
            payload = load_json(usage_path)
        except Exception:
            instances.append(
                {
                    "instance": inst_dir.name,
                    "status": "error",
                    "usage_path": str(usage_path),
                    "error": "failed to parse usage.json",
                }
            )
            has_unknown_cost = True
            continue

        inst_usage = payload.get("usage")
        if isinstance(inst_usage, dict):
            merge_usage(all_usage, inst_usage)

        cost_obj = payload.get("cost")
        inst_cost = None
        if isinstance(cost_obj, dict):
            inst_cost = _to_float_or_none(cost_obj.get("cost_usd"))
        if inst_cost is None:
            has_unknown_cost = True
        else:
            total_cost += inst_cost

        instances.append(
            {
                "instance": str(payload.get("instance", inst_dir.name)),
                "status": str(payload.get("status", "unknown")),
                "cost_usd": inst_cost,
                "usage_path": str(usage_path),
            }
        )

    out = {
        "repo": repo_out_root.name,
        "provider": provider,
        "model": model,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "instance_count": len(instances),
        "all_usage": all_usage,
        "all_cost_usd": None if has_unknown_cost else total_cost,
        "instances": instances,
    }
    dump_json(repo_out_root / "usage.json", out)


def extract_first_json_object(text: str) -> Optional[Any]:
    text = text.strip()
    if not text:
        return None

    # direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # strip fenced code blocks
    code_fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if code_fence:
        cand = code_fence.group(1)
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            pass

    # brace scanning fallback
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    cand = text[start : i + 1]
                    try:
                        return json.loads(cand)
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)

    return None


def _type_label(x: Any) -> str:
    if isinstance(x, bool):
        return "bool"
    if isinstance(x, int):
        return "int"
    if isinstance(x, float):
        return "float"
    if isinstance(x, str):
        return "str"
    if isinstance(x, list):
        return "list"
    if isinstance(x, dict):
        return "dict"
    return type(x).__name__


def validate_against_template(answer: Any, template: Any, path: str = "$") -> List[str]:
    errors: List[str] = []

    if isinstance(template, dict):
        if not isinstance(answer, dict):
            return [f"{path}: expected dict, got {_type_label(answer)}"]
        for key, tval in template.items():
            if key not in answer:
                errors.append(f"{path}: missing key '{key}'")
                continue
            errors.extend(validate_against_template(answer[key], tval, f"{path}.{key}"))
        return errors

    if isinstance(template, list):
        if not isinstance(answer, list):
            return [f"{path}: expected list, got {_type_label(answer)}"]
        # No strict shape constraints from template lists unless items are provided.
        if template:
            item_t = template[0]
            for i, item in enumerate(answer):
                errors.extend(validate_against_template(item, item_t, f"{path}[{i}]"))
        return errors

    if isinstance(template, str):
        token = template.strip().lower()
        if token in {"int", "integer"} and not (isinstance(answer, int) and not isinstance(answer, bool)):
            return [f"{path}: expected int, got {_type_label(answer)}"]
        if token in {"float", "number"} and not (
            (isinstance(answer, int) and not isinstance(answer, bool)) or isinstance(answer, float)
        ):
            return [f"{path}: expected float/number, got {_type_label(answer)}"]
        if token in {"str", "string"} and not isinstance(answer, str):
            return [f"{path}: expected str, got {_type_label(answer)}"]
        if token in {"bool", "boolean"} and not isinstance(answer, bool):
            return [f"{path}: expected bool, got {_type_label(answer)}"]
        if token in {"list", "array"} and not isinstance(answer, list):
            return [f"{path}: expected list, got {_type_label(answer)}"]
        if token in {"dict", "object"} and not isinstance(answer, dict):
            return [f"{path}: expected dict, got {_type_label(answer)}"]
        return []

    # If template has concrete literal values, match type only (keeps template flexible).
    if type(answer) is not type(template):
        return [f"{path}: expected {_type_label(template)}, got {_type_label(answer)}"]
    return []


def _json_loads_if_possible(value: Any) -> Tuple[Any, bool]:
    if not isinstance(value, str):
        return value, False
    s = value.strip()
    if not s:
        return value, False
    try:
        return json.loads(s), True
    except json.JSONDecodeError:
        return value, False


def _coerce_to_bool(value: Any) -> Tuple[Any, bool]:
    if isinstance(value, bool):
        return value, False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value), True
    if isinstance(value, str):
        s = value.strip().lower()
        true_set = {"true", "t", "yes", "y", "on", "1"}
        false_set = {"false", "f", "no", "n", "off", "0", ""}
        if s in true_set:
            return True, True
        if s in false_set:
            return False, True
        parsed, changed = _json_loads_if_possible(value)
        if changed:
            return _coerce_to_bool(parsed)
    return value, False


def _coerce_to_int(value: Any) -> Tuple[Any, bool]:
    if isinstance(value, bool):
        return int(value), True
    if isinstance(value, int):
        return value, False
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            return int(value), True
        return value, False
    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"true", "t", "yes", "y", "on"}:
            return 1, True
        if s in {"false", "f", "no", "n", "off"}:
            return 0, True
        s_num = s.replace(",", "").replace("_", "")
        if re.fullmatch(r"[+-]?\d+", s_num):
            try:
                return int(s_num), True
            except Exception:
                pass
        if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", s_num):
            try:
                fv = float(s_num)
                if math.isfinite(fv) and fv.is_integer():
                    return int(fv), True
            except Exception:
                pass
        parsed, changed = _json_loads_if_possible(value)
        if changed:
            return _coerce_to_int(parsed)
    return value, False


def _coerce_to_float(value: Any) -> Tuple[Any, bool]:
    if isinstance(value, bool):
        return float(value), True
    if isinstance(value, int) and not isinstance(value, bool):
        return float(value), True
    if isinstance(value, float):
        return value, False
    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"true", "t", "yes", "y", "on"}:
            return 1.0, True
        if s in {"false", "f", "no", "n", "off"}:
            return 0.0, True
        s_num = s.replace(",", "").replace("_", "")
        try:
            return float(s_num), True
        except Exception:
            pass
        parsed, changed = _json_loads_if_possible(value)
        if changed:
            return _coerce_to_float(parsed)
    return value, False


def _coerce_to_str(value: Any) -> Tuple[Any, bool]:
    if isinstance(value, str):
        return value, False
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")), True
    if value is None:
        return "null", True
    return str(value), True


def _coerce_to_list(value: Any) -> Tuple[Any, bool]:
    if isinstance(value, list):
        return value, False
    if isinstance(value, (tuple, set)):
        return list(value), True
    if isinstance(value, str):
        parsed, changed = _json_loads_if_possible(value)
        if changed:
            if isinstance(parsed, list):
                return parsed, True
            return [parsed], True
    if value is None:
        return [], True
    return [value], True


def _coerce_to_dict(value: Any) -> Tuple[Any, bool]:
    if isinstance(value, dict):
        return value, False
    if isinstance(value, str):
        parsed, changed = _json_loads_if_possible(value)
        if changed:
            if isinstance(parsed, dict):
                return parsed, True
            if isinstance(parsed, list):
                try:
                    return dict(parsed), True
                except Exception:
                    pass
    if isinstance(value, (list, tuple)):
        try:
            return dict(value), True
        except Exception:
            return value, False
    return value, False


def _template_kind(template: Any) -> Optional[str]:
    if isinstance(template, str):
        token = template.strip().lower()
        if token in {"int", "integer"}:
            return "int"
        if token in {"float", "number"}:
            return "float"
        if token in {"str", "string"}:
            return "str"
        if token in {"bool", "boolean"}:
            return "bool"
        if token in {"list", "array"}:
            return "list"
        if token in {"dict", "object"}:
            return "dict"
        return "str"
    if isinstance(template, bool):
        return "bool"
    if isinstance(template, int):
        return "int"
    if isinstance(template, float):
        return "float"
    if isinstance(template, list):
        return "list"
    if isinstance(template, dict):
        return "dict"
    return None


def _coerce_by_kind(value: Any, kind: str) -> Tuple[Any, bool]:
    if kind == "bool":
        return _coerce_to_bool(value)
    if kind == "int":
        return _coerce_to_int(value)
    if kind == "float":
        return _coerce_to_float(value)
    if kind == "str":
        return _coerce_to_str(value)
    if kind == "list":
        return _coerce_to_list(value)
    if kind == "dict":
        return _coerce_to_dict(value)
    return value, False


def coerce_against_template(answer: Any, template: Any, path: str = "$") -> Tuple[Any, List[str]]:
    notes: List[str] = []

    if isinstance(template, dict):
        container, changed = _coerce_to_dict(answer)
        if changed:
            notes.append(f"{path}: coerced {_type_label(answer)}->dict")
        if not isinstance(container, dict):
            return container, notes
        out = dict(container)
        for key, tval in template.items():
            if key not in out:
                continue
            coerced, child_notes = coerce_against_template(out[key], tval, f"{path}.{key}")
            out[key] = coerced
            notes.extend(child_notes)
        return out, notes

    if isinstance(template, list):
        container, changed = _coerce_to_list(answer)
        if changed:
            notes.append(f"{path}: coerced {_type_label(answer)}->list")
        if not isinstance(container, list):
            return container, notes
        if not template:
            return container, notes
        item_template = template[0]
        out_list: List[Any] = []
        for idx, item in enumerate(container):
            coerced, child_notes = coerce_against_template(item, item_template, f"{path}[{idx}]")
            out_list.append(coerced)
            notes.extend(child_notes)
        return out_list, notes

    kind = _template_kind(template)
    if kind is None:
        return answer, notes

    coerced, changed = _coerce_by_kind(answer, kind)
    if changed:
        notes.append(f"{path}: coerced {_type_label(answer)}->{kind}")
    return coerced, notes


# ---------------------------
# RepoMap + read-only tools
# ---------------------------


@dataclass
class ToolResult:
    ok: bool
    payload: Dict[str, Any]


class _SilentAiderIO:
    encoding = "utf-8"

    def __init__(self, encoding: str = "utf-8") -> None:
        self.encoding = encoding

    def tool_output(self, *_args: Any, **_kwargs: Any) -> None:
        return

    def tool_error(self, *_args: Any, **_kwargs: Any) -> None:
        return

    def tool_warning(self, *_args: Any, **_kwargs: Any) -> None:
        return

    def read_text(self, fname: str) -> str:
        try:
            return Path(fname).read_text(encoding=self.encoding, errors="replace")
        except Exception:
            return ""


class _FallbackTokenizer:
    def encode(self, text: str) -> List[int]:
        # Rough token estimate fallback when aider's model tokenizer is unavailable.
        approx = max(1, len(text) // 4)
        return [0] * approx


class _FallbackMainModel:
    def __init__(self) -> None:
        self.tokenizer = _FallbackTokenizer()

    def token_count(self, text: str) -> int:
        return len(self.tokenizer.encode(text))


_REPO_FILE_CACHE: Dict[str, List[str]] = {}
_REPO_MAP_CACHE: Dict[Tuple[str, int], str] = {}
INSTANCE_PREVIEW_LIMIT = 60


class ReadOnlyRepoTools:
    TEXT_SUFFIXES = {
        ".py",
        ".pyi",
        ".md",
        ".txt",
        ".rst",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".sh",
        ".bash",
        ".zsh",
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".hpp",
        ".java",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".go",
        ".rs",
        ".sql",
        ".xml",
        ".html",
        ".css",
    }
    IGNORE_DIRS = {".git", ".hg", ".svn", ".tox", ".venv", "venv", "node_modules", "__pycache__"}

    def __init__(
        self,
        *,
        repo_root: Path,
        instance_dir: Path,
        repomap_tokens: int,
        max_read_lines: int,
        max_read_chars: int,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.instance_dir = instance_dir.resolve()
        self.repomap_tokens = repomap_tokens
        self.max_read_lines = max_read_lines
        self.max_read_chars = max_read_chars

        if not self.repo_root.exists():
            raise RuntimeError(f"Repository root does not exist: {self.repo_root}")
        if not self.instance_dir.exists():
            raise RuntimeError(f"Instance dir does not exist: {self.instance_dir}")

        self._repomap = self._build_repomap()

    def _build_repomap(self) -> Any:
        try:
            from aider.repomap import RepoMap
        except Exception as exc:  # pragma: no cover - runtime dependency
            raise RuntimeError(
                "Failed to import aider.repomap.RepoMap. Install with: pip install aider-chat"
            ) from exc

        io_obj = _SilentAiderIO()
        kwargs = {
            "root": str(self.repo_root),
            "map_tokens": int(self.repomap_tokens),
            "io": io_obj,
            "main_model": _FallbackMainModel(),
        }
        try:
            return RepoMap(**kwargs)
        except TypeError:
            # Older/newer signatures.
            sig = inspect.signature(RepoMap.__init__)
            filtered = {k: v for k, v in kwargs.items() if k in sig.parameters}
            return RepoMap(**filtered)

    def _all_repo_files(self) -> List[str]:
        key = str(self.repo_root)
        if key in _REPO_FILE_CACHE:
            return _REPO_FILE_CACHE[key]

        out: List[str] = []
        for path in self.repo_root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in self.IGNORE_DIRS for part in path.parts):
                continue
            if path.suffix.lower() and path.suffix.lower() not in self.TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 1_000_000:
                    continue
            except OSError:
                continue
            out.append(str(path))

        _REPO_FILE_CACHE[key] = sorted(out)
        return _REPO_FILE_CACHE[key]

    def _is_under_allowed_roots(self, p: Path) -> bool:
        try:
            p.relative_to(self.repo_root)
            return True
        except ValueError:
            pass
        try:
            p.relative_to(self.instance_dir)
            return True
        except ValueError:
            return False

    def _known_repo_prefixes(self) -> List[str]:
        base = self.repo_root.name.lower()
        prefixes = {
            base,
            base.replace("-", "_"),
            base.replace("_", "-"),
            "sympy",
            "keras",
            "xarray",
            "faker",
            "telegram",
            "telegram_bot",
            "python-telegram-bot",
        }
        return sorted(x for x in prefixes if x)

    def _to_user_path(self, p: Path) -> str:
        resolved = p.resolve(strict=False)
        try:
            rel = resolved.relative_to(self.repo_root)
            return str(rel) if str(rel) else "."
        except ValueError:
            pass
        try:
            rel = resolved.relative_to(self.instance_dir)
            return str(rel) if str(rel) else "."
        except ValueError:
            return str(resolved)

    def _resolve_user_path(self, raw_path: str) -> Path:
        raw = raw_path.strip()
        if not raw:
            raise ValueError("path cannot be empty")

        candidate_paths: List[Path] = []
        seen_candidates: set = set()
        known_prefixes = self._known_repo_prefixes()

        def _add_candidate(path: Path) -> None:
            key = str(path)
            if key in seen_candidates:
                return
            seen_candidates.add(key)
            candidate_paths.append(path)

        p = Path(raw)
        if p.is_absolute():
            _add_candidate(p)
            # Some model outputs duplicate repo folder prefix: <repo>/<repo>/...
            resolved_abs = p.resolve(strict=False)
            try:
                rel = resolved_abs.relative_to(self.repo_root)
                if rel.parts and rel.parts[0].lower() in known_prefixes and len(rel.parts) > 1:
                    _add_candidate(self.repo_root / Path(*rel.parts[1:]))
            except ValueError:
                pass
        else:
            _add_candidate(self.repo_root / p)
            _add_candidate(self.instance_dir / p)
            _add_candidate(self.instance_dir / "files" / p)

            # Common benchmark hint paths often include top-level package dir
            # (e.g. sympy/core/...) while repo_root is already that package root.
            parts = p.parts
            if len(parts) > 1:
                first = parts[0].lower()
                if first in known_prefixes:
                    stripped = Path(*parts[1:])
                    _add_candidate(self.repo_root / stripped)
                    _add_candidate(self.instance_dir / stripped)
                    _add_candidate(self.instance_dir / "files" / stripped)

            # Instance fixtures are often under files/<repo_prefix>/...
            for prefix in known_prefixes:
                _add_candidate(self.instance_dir / "files" / prefix / p)

            # tests/qa/... generally lives under instance_dir/files/tests/qa/...
            if str(p).startswith("tests/"):
                _add_candidate(self.instance_dir / "files" / p)
                for prefix in known_prefixes:
                    _add_candidate(self.instance_dir / "files" / prefix / p)

        allowed_candidates: List[Path] = []
        for cand in candidate_paths:
            resolved = cand.resolve(strict=False)
            if self._is_under_allowed_roots(resolved):
                allowed_candidates.append(resolved)

        # Prefer an existing path to avoid unnecessary failed read attempts.
        for resolved in allowed_candidates:
            if resolved.exists():
                return resolved

        # If absolute path points at instance_dir/tests/... but files are under
        # instance_dir/files/tests/..., patch it transparently.
        for resolved in allowed_candidates:
            try:
                rel_to_instance = resolved.relative_to(self.instance_dir)
            except ValueError:
                continue
            if rel_to_instance.parts and rel_to_instance.parts[0] == "tests":
                fixed = (self.instance_dir / "files" / rel_to_instance).resolve(strict=False)
                if self._is_under_allowed_roots(fixed) and fixed.exists():
                    return fixed

        if allowed_candidates:
            return allowed_candidates[0]

        raise ValueError(
            f"path '{raw_path}' is outside allowed roots: {self.repo_root} and {self.instance_dir}"
        )

    def get_repo_map(self, focus_paths: Optional[List[str]] = None) -> ToolResult:
        cache_key = (str(self.repo_root), int(self.repomap_tokens))

        chat_files: List[str] = []
        if focus_paths:
            for p in focus_paths:
                try:
                    rp = self._resolve_user_path(p)
                except ValueError:
                    continue
                if rp.is_file():
                    chat_files.append(str(rp))

        if not chat_files and cache_key in _REPO_MAP_CACHE:
            return ToolResult(
                ok=True,
                payload={
                    "repo_root": self._to_user_path(self.repo_root),
                    "repo_file_count": len(self._all_repo_files()),
                    "focus_file_count": 0,
                    "repo_map": _REPO_MAP_CACHE[cache_key],
                },
            )

        all_files = self._all_repo_files()

        try:
            repomap_text = self._repomap.get_repo_map(chat_files=chat_files, other_files=all_files)
        except TypeError:
            # Defensive fallback for positional signatures.
            repomap_text = self._repomap.get_repo_map(chat_files, all_files)

        if not chat_files and repomap_text:
            _REPO_MAP_CACHE[cache_key] = repomap_text

        if not repomap_text:
            repomap_text = ""

        return ToolResult(
            ok=True,
            payload={
                "repo_root": self._to_user_path(self.repo_root),
                "repo_file_count": len(all_files),
                "focus_file_count": len(chat_files),
                "repo_map": repomap_text,
            },
        )

    def list_dir(self, path: str = ".", max_entries: int = 200) -> ToolResult:
        try:
            target = self._resolve_user_path(path)
        except ValueError as exc:
            return ToolResult(ok=False, payload={"error": str(exc)})

        if not target.exists():
            return ToolResult(ok=False, payload={"error": f"path does not exist: {self._to_user_path(target)}"})
        if not target.is_dir():
            return ToolResult(ok=False, payload={"error": f"not a directory: {self._to_user_path(target)}"})

        max_entries = max(1, min(int(max_entries), 1000))
        entries = []
        for item in sorted(target.iterdir(), key=lambda p: p.name)[:max_entries]:
            entry = {
                "name": item.name,
                "path": self._to_user_path(item),
                "type": "dir" if item.is_dir() else "file",
            }
            if item.is_file():
                try:
                    entry["size"] = item.stat().st_size
                except OSError:
                    pass
            entries.append(entry)

        return ToolResult(ok=True, payload={"path": self._to_user_path(target), "entries": entries})

    def read_file(self, path: str, start_line: int = 1, end_line: int = 250) -> ToolResult:
        try:
            target = self._resolve_user_path(path)
        except ValueError as exc:
            return ToolResult(ok=False, payload={"error": str(exc)})

        if not target.exists():
            return ToolResult(ok=False, payload={"error": f"path does not exist: {self._to_user_path(target)}"})
        if not target.is_file():
            return ToolResult(ok=False, payload={"error": f"not a file: {self._to_user_path(target)}"})

        start_line = max(1, int(start_line))
        end_line = max(start_line, int(end_line))
        if end_line - start_line + 1 > self.max_read_lines:
            end_line = start_line + self.max_read_lines - 1

        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return ToolResult(ok=False, payload={"error": f"failed reading file: {exc}"})

        lines = text.splitlines()
        total = len(lines)
        s_idx = start_line - 1
        e_idx = min(end_line, total)

        selected = lines[s_idx:e_idx]
        numbered = "\n".join(f"{i + start_line}:{line}" for i, line in enumerate(selected))
        truncated = False
        if len(numbered) > self.max_read_chars:
            numbered = numbered[: self.max_read_chars]
            truncated = True

        return ToolResult(
            ok=True,
            payload={
                "path": self._to_user_path(target),
                "start_line": start_line,
                "end_line": e_idx,
                "total_lines": total,
                "truncated": truncated,
                "content": numbered,
            },
        )


TOOL_DESCRIPTIONS = {
    "get_repo_map": "Return aider RepoMap context for the repository. Use this first to find relevant files.",
    "list_dir": "List directory entries in allowed roots (repo root and current instance directory).",
    "read_file": "Read file content by line range. Read-only.",
}

TOOL_INPUT_SCHEMAS = {
    "get_repo_map": {
        "type": "object",
        "properties": {
            "focus_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional file paths to focus the repo map.",
            }
        },
    },
    "list_dir": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path (absolute under /testbed or relative to repo/instance).",
                "default": ".",
            },
            "max_entries": {
                "type": "integer",
                "default": 200,
                "minimum": 1,
                "maximum": 1000,
            },
        },
    },
    "read_file": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path (absolute under /testbed or relative to repo/instance).",
            },
            "start_line": {
                "type": "integer",
                "default": 1,
                "minimum": 1,
            },
            "end_line": {
                "type": "integer",
                "default": 250,
                "minimum": 1,
            },
        },
        "required": ["path"],
    },
}


# ---------------------------
# Provider adapters
# ---------------------------


class ProviderRunner:
    def __init__(
        self,
        provider: str,
        model: str,
        max_tool_rounds: int,
        temperature: float = 0.0,
        trace: Optional[Callable[[str], None]] = None,
    ):
        self.provider = provider
        self.model = model
        self.max_tool_rounds = max_tool_rounds
        self.temperature = temperature
        self.trace = trace
        self._usage = empty_usage(provider, model)

    def _t(self, msg: str) -> None:
        if self.trace:
            self.trace(msg)

    @staticmethod
    def _get_field(obj: Any, key: str, default: Any = None) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _inc_usage(self, key: str, value: Any) -> None:
        n = _to_int_or_none(value)
        if n is None:
            return
        self._usage[key] = int(self._usage.get(key, 0)) + max(0, n)

    def _record_usage(self, source: str, usage_obj: Any) -> None:
        self._inc_usage("requests", 1)
        if usage_obj is None:
            self._inc_usage("usage_missing_requests", 1)
            return

        g = self._get_field
        if source.startswith("openai-chat") or source.startswith("openai-legacy"):
            self._inc_usage("input_tokens", g(usage_obj, "prompt_tokens"))
            self._inc_usage("output_tokens", g(usage_obj, "completion_tokens"))
            self._inc_usage("total_tokens", g(usage_obj, "total_tokens"))
            pdetails = g(usage_obj, "prompt_tokens_details")
            cdetails = g(usage_obj, "completion_tokens_details")
            self._inc_usage("cached_input_tokens", g(pdetails, "cached_tokens"))
            self._inc_usage("reasoning_tokens", g(cdetails, "reasoning_tokens"))
        elif source.startswith("openai-responses"):
            self._inc_usage("input_tokens", g(usage_obj, "input_tokens"))
            self._inc_usage("output_tokens", g(usage_obj, "output_tokens"))
            self._inc_usage("total_tokens", g(usage_obj, "total_tokens"))
            idetails = g(usage_obj, "input_tokens_details")
            odetails = g(usage_obj, "output_tokens_details")
            self._inc_usage("cached_input_tokens", g(idetails, "cached_tokens"))
            self._inc_usage("cached_input_tokens", g(idetails, "cached_input_tokens"))
            self._inc_usage("reasoning_tokens", g(odetails, "reasoning_tokens"))
        elif source.startswith("gemini"):
            self._inc_usage("input_tokens", g(usage_obj, "prompt_token_count"))
            self._inc_usage("output_tokens", g(usage_obj, "candidates_token_count"))
            self._inc_usage("total_tokens", g(usage_obj, "total_token_count"))
            self._inc_usage("cached_input_tokens", g(usage_obj, "cached_content_token_count"))
        elif source.startswith("anthropic"):
            self._inc_usage("input_tokens", g(usage_obj, "input_tokens"))
            self._inc_usage("output_tokens", g(usage_obj, "output_tokens"))
            self._inc_usage("cache_creation_input_tokens", g(usage_obj, "cache_creation_input_tokens"))
            self._inc_usage("cache_read_input_tokens", g(usage_obj, "cache_read_input_tokens"))
            # Anthropic cache read tokens are input-side cached tokens.
            self._inc_usage("cached_input_tokens", g(usage_obj, "cache_read_input_tokens"))
        else:
            self._inc_usage("input_tokens", g(usage_obj, "input_tokens"))
            self._inc_usage("output_tokens", g(usage_obj, "output_tokens"))
            self._inc_usage("total_tokens", g(usage_obj, "total_tokens"))

        if int(self._usage.get("total_tokens", 0)) <= 0:
            self._usage["total_tokens"] = int(self._usage.get("input_tokens", 0)) + int(
                self._usage.get("output_tokens", 0)
            )

    def usage_summary(self) -> Dict[str, Any]:
        out = dict(self._usage)
        if int(out.get("total_tokens", 0)) <= 0:
            out["total_tokens"] = int(out.get("input_tokens", 0)) + int(out.get("output_tokens", 0))
        return out

    def run(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tool_callback,
    ) -> str:
        if self.provider == "openai":
            return self._run_openai(system_prompt=system_prompt, user_prompt=user_prompt, tool_callback=tool_callback)
        if self.provider == "gemini":
            return self._run_gemini(system_prompt=system_prompt, user_prompt=user_prompt, tool_callback=tool_callback)
        if self.provider == "anthropic":
            return self._run_anthropic(system_prompt=system_prompt, user_prompt=user_prompt, tool_callback=tool_callback)
        raise ValueError(f"Unsupported provider: {self.provider}")

    def _run_openai(self, *, system_prompt: str, user_prompt: str, tool_callback) -> str:
        import openai

        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("openai_api_key")
        has_new_client = hasattr(openai, "OpenAI")
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        if has_new_client:
            client = openai.OpenAI(api_key=api_key) if api_key else openai.OpenAI()
            responses_err: Optional[Exception] = None
            try:
                return self._run_openai_responses(
                    client=client,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    tool_callback=tool_callback,
                )
            except Exception as exc:
                responses_err = exc
                self._t(
                    f"[openai] responses fallback triggered: {exc.__class__.__name__}: {exc}"
                )

            try:
                return self._run_openai_chat(
                    client=client,
                    messages=messages,
                    tool_callback=tool_callback,
                )
            except Exception as chat_exc:
                if responses_err is None:
                    raise
                raise RuntimeError(
                    "OpenAI run failed with both endpoints: "
                    f"responses=({responses_err.__class__.__name__}: {responses_err}); "
                    f"chat.completions=({chat_exc.__class__.__name__}: {chat_exc})"
                ) from chat_exc

        # Legacy openai SDK (<1.x), compatible with Python 3.8 images.
        openai.api_key = api_key
        functions = [
            {
                "name": name,
                "description": TOOL_DESCRIPTIONS[name],
                "parameters": TOOL_INPUT_SCHEMAS[name],
            }
            for name in ["get_repo_map", "list_dir", "read_file"]
        ]

        for _ in range(self.max_tool_rounds):
            self._t("[openai-legacy] request")
            resp = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                functions=functions,
                function_call="auto",
                temperature=self.temperature,
            )
            self._record_usage("openai-legacy", self._get_field(resp, "usage"))
            msg = resp["choices"][0]["message"]
            self._t(f"[openai-legacy] assistant: {msg.get('content', '') or ''}")
            function_call = msg.get("function_call")
            if function_call:
                fn_name = function_call.get("name", "")
                args_raw = function_call.get("arguments", "{}")
                self._t(f"[openai-legacy] function_call {fn_name} args={args_raw}")
                try:
                    args = json.loads(args_raw)
                except json.JSONDecodeError:
                    args = {}

                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.get("content", ""),
                        "function_call": function_call,
                    }
                )
                result = tool_callback(fn_name, args)
                messages.append(
                    {
                        "role": "function",
                        "name": fn_name,
                        "content": json.dumps(result),
                    }
                )
                continue

            return msg.get("content", "") or ""

        raise RuntimeError("OpenAI legacy run exceeded max tool rounds without final answer")

    def _run_openai_chat(self, *, client, messages: List[Dict[str, Any]], tool_callback) -> str:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": TOOL_DESCRIPTIONS[name],
                    "parameters": TOOL_INPUT_SCHEMAS[name],
                },
            }
            for name in ["get_repo_map", "list_dir", "read_file"]
        ]

        for _ in range(self.max_tool_rounds):
            self._t("[openai-chat] request")
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=self.temperature,
            )
            self._record_usage("openai-chat", getattr(resp, "usage", None))
            msg = resp.choices[0].message
            self._t(f"[openai-chat] assistant: {msg.content or ''}")

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    self._t(f"[openai-chat] tool_call {tc.function.name} args={tc.function.arguments}")
                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
                    }
                )

                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    args_raw = tc.function.arguments or "{}"
                    try:
                        args = json.loads(args_raw)
                    except json.JSONDecodeError:
                        args = {}
                    result = tool_callback(fn_name, args)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": fn_name,
                            "content": json.dumps(result),
                        }
                    )
                continue

            return msg.content or ""

        raise RuntimeError("OpenAI chat.completions run exceeded max tool rounds without final answer")

    def _run_openai_responses(self, *, client, system_prompt: str, user_prompt: str, tool_callback) -> str:
        def _g(obj: Any, key: str, default: Any = None) -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        tools = [
            {
                "type": "function",
                "name": name,
                "description": TOOL_DESCRIPTIONS[name],
                "parameters": TOOL_INPUT_SCHEMAS[name],
            }
            for name in ["get_repo_map", "list_dir", "read_file"]
        ]

        response = client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
            tools=tools,
            temperature=self.temperature,
        )
        self._record_usage("openai-responses", getattr(response, "usage", None))

        for _ in range(self.max_tool_rounds):
            self._t("[openai-responses] request")
            output_items = list(getattr(response, "output", []) or [])
            function_calls = [item for item in output_items if _g(item, "type", "") == "function_call"]

            if function_calls:
                tool_outputs: List[Dict[str, Any]] = []
                for fc in function_calls:
                    fn_name = str(_g(fc, "name", "") or "")
                    args_raw = str(_g(fc, "arguments", "") or "{}")
                    self._t(f"[openai-responses] function_call {fn_name} args={args_raw}")
                    try:
                        args = json.loads(args_raw)
                    except json.JSONDecodeError:
                        args = {}
                    result = tool_callback(fn_name, args)
                    call_id = str(_g(fc, "call_id", "") or _g(fc, "id", "") or "")
                    tool_outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": json.dumps(result),
                        }
                    )

                response = client.responses.create(
                    model=self.model,
                    previous_response_id=getattr(response, "id", None),
                    input=tool_outputs,
                    tools=tools,
                    temperature=self.temperature,
                )
                self._record_usage("openai-responses", getattr(response, "usage", None))
                continue

            text = getattr(response, "output_text", None)
            if isinstance(text, str) and text.strip():
                self._t(f"[openai-responses] assistant: {text}")
                return text

            text_parts: List[str] = []
            for item in output_items:
                if _g(item, "type", "") != "message":
                    continue
                for part in list(_g(item, "content", []) or []):
                    ptype = _g(part, "type", "")
                    if ptype in {"output_text", "text"}:
                        value = _g(part, "text", "")
                        if value:
                            text_parts.append(str(value))
            joined = "\n".join(x for x in text_parts if x).strip()
            self._t(f"[openai-responses] assistant: {joined}")
            if joined:
                return joined

            # Defensive fallback when API returns no assistant text and no calls.
            return ""

        raise RuntimeError("OpenAI responses run exceeded max tool rounds without final answer")

    def _run_gemini(self, *, system_prompt: str, user_prompt: str, tool_callback) -> str:
        from google import genai
        from google.genai import types

        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)

        fn_decls = [
            types.FunctionDeclaration(
                name=name,
                description=TOOL_DESCRIPTIONS[name],
                parameters=TOOL_INPUT_SCHEMAS[name],
            )
            for name in ["get_repo_map", "list_dir", "read_file"]
        ]

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[types.Tool(function_declarations=fn_decls)],
            temperature=self.temperature,
        )

        contents: List[Any] = [types.UserContent(parts=[types.Part.from_text(text=user_prompt)])]

        for _ in range(self.max_tool_rounds):
            self._t("[gemini] request")
            resp = client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            self._record_usage("gemini", getattr(resp, "usage_metadata", None))

            function_calls = list(resp.function_calls or [])
            if function_calls:
                for fc in function_calls:
                    fn_name = fc.name or ""
                    fn_args = fc.args or {}
                    self._t(f"[gemini] function_call {fn_name} args={json.dumps(fn_args, ensure_ascii=False)}")
                    contents.append(
                        types.ModelContent(
                            parts=[types.Part.from_function_call(name=fn_name, args=fn_args)]
                        )
                    )
                    result = tool_callback(fn_name, fn_args)
                    contents.append(
                        types.UserContent(
                            parts=[types.Part.from_function_response(name=fn_name, response=result)]
                        )
                    )
                continue

            self._t(f"[gemini] assistant: {resp.text or ''}")
            return resp.text or ""

        raise RuntimeError("Gemini run exceeded max tool rounds without final answer")

    def _run_anthropic(self, *, system_prompt: str, user_prompt: str, tool_callback) -> str:
        import anthropic

        client = anthropic.Anthropic()
        tools = [
            {
                "name": name,
                "description": TOOL_DESCRIPTIONS[name],
                "input_schema": TOOL_INPUT_SCHEMAS[name],
            }
            for name in ["get_repo_map", "list_dir", "read_file"]
        ]

        messages: List[Dict[str, Any]] = [{"role": "user", "content": user_prompt}]

        for _ in range(self.max_tool_rounds):
            self._t("[anthropic] request")
            resp = client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=tools,
                temperature=self.temperature,
            )
            self._record_usage("anthropic", getattr(resp, "usage", None))

            tool_uses = [block for block in resp.content if block.type == "tool_use"]
            if tool_uses:
                assistant_blocks = [b.model_dump() for b in resp.content]
                for block in tool_uses:
                    self._t(
                        f"[anthropic] tool_use {block.name} args={json.dumps(block.input or {}, ensure_ascii=False)}"
                    )
                messages.append({"role": "assistant", "content": assistant_blocks})

                tool_results = []
                for block in tool_uses:
                    result = tool_callback(block.name, block.input or {})
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        }
                    )
                messages.append({"role": "user", "content": tool_results})
                continue

            text_parts = [block.text for block in resp.content if block.type == "text"]
            self._t(f"[anthropic] assistant: {' '.join(text_parts).strip()}")
            return "\n".join(text_parts).strip()

        raise RuntimeError("Anthropic run exceeded max tool rounds without final answer")


# ---------------------------
# Worker mode
# ---------------------------


def make_system_prompt() -> str:
    return (
        "Solve repository QA in read-only mode with tool calls only.\n"
        "Rules:\n"
        "1. Call get_repo_map first, then use list_dir/read_file only as needed.\n"
        "2. Prefer relative paths. Repo files are usually like src/...; instance files are usually files/....\n"
        "3. Minimize unnecessary reads and repeated failed paths.\n"
        "4. Final output must be exactly one JSON object matching template_answer keys and value types.\n"
        "5. Do not output markdown or explanations in the final answer."
    )


def build_user_prompt(
    *,
    question_data: Dict[str, Any],
    repo_root: Path,
    instance_dir: Path,
    instance_files_preview: List[str],
) -> str:
    question = question_data.get("question", "")
    template_answer = question_data.get("template_answer", {})
    question_kind = question_data.get("question_kind", "unknown")
    template_str = json.dumps(template_answer, sort_keys=True, separators=(",", ":"))

    preview_files = instance_files_preview[:INSTANCE_PREVIEW_LIMIT]
    preview_lines = [f"- {p}" for p in preview_files]
    omitted_count = len(instance_files_preview) - len(preview_files)
    if omitted_count > 0:
        preview_lines.append(f"- ... ({omitted_count} more files)")
    preview_str = "\n".join(preview_lines)

    return (
        f"Repository root: {repo_root}\n"
        f"Instance directory: {instance_dir}\n"
        f"Question kind: {question_kind}\n\n"
        f"Question:\n{question}\n\n"
        f"Template answer (must match exactly):\n{template_str}\n\n"
        "Instance file preview (you can read these and repository files with tools):\n"
        f"{preview_str if preview_str else '- (no files)'}\n\n"
        "Task: return only the final JSON answer object."
    )


def run_single_instance(
    *,
    provider: str,
    model: str,
    question_path: Path,
    repo_root: Path,
    repomap_tokens: int,
    max_tool_rounds: int,
    max_read_lines: int,
    max_read_chars: int,
    temperature: float,
    max_repair_rounds: int,
    trace: Optional[Callable[[str], None]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    question_data = load_json(question_path)
    instance_dir = question_path.parent

    instance_files = []
    files_dir = instance_dir / "files"
    if files_dir.exists():
        instance_files = [str(p.relative_to(instance_dir)) for p in sorted(files_dir.rglob("*")) if p.is_file()]

    tools = ReadOnlyRepoTools(
        repo_root=repo_root,
        instance_dir=instance_dir,
        repomap_tokens=repomap_tokens,
        max_read_lines=max_read_lines,
        max_read_chars=max_read_chars,
    )

    def _trace_tool_result(name: str, payload: Dict[str, Any]) -> None:
        if not trace:
            return
        try:
            serialized = json.dumps(payload, ensure_ascii=False)
        except Exception:
            serialized = str(payload)
        max_chars = 5000
        if len(serialized) > max_chars:
            serialized = serialized[:max_chars] + "...<truncated>"
        trace(f"[tool] send_to_llm {name} result={serialized}")

    def tool_callback(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if trace:
            trace(f"[tool] call {name} args={json.dumps(args, ensure_ascii=False)}")
        if name == "get_repo_map":
            result = tools.get_repo_map(focus_paths=args.get("focus_paths"))
            out = {"ok": result.ok, **result.payload}
            if trace:
                preview = (out.get("repo_map", "") or "")[:500].replace("\n", " ")
                trace(f"[tool] result {name} ok={out.get('ok')} preview={preview}")
            _trace_tool_result(name, out)
            return out
        if name == "list_dir":
            result = tools.list_dir(path=args.get("path", "."), max_entries=args.get("max_entries", 200))
            out = {"ok": result.ok, **result.payload}
            if trace:
                trace(f"[tool] result {name} ok={out.get('ok')} entries={len(out.get('entries', []))}")
            _trace_tool_result(name, out)
            return out
        if name == "read_file":
            result = tools.read_file(
                path=args.get("path", ""),
                start_line=args.get("start_line", 1),
                end_line=args.get("end_line", 250),
            )
            out = {"ok": result.ok, **result.payload}
            if trace:
                trace(
                    f"[tool] result {name} ok={out.get('ok')} path={out.get('path')} "
                    f"lines={out.get('start_line')}-{out.get('end_line')}"
                )
            _trace_tool_result(name, out)
            return out
        return {"ok": False, "error": f"unknown tool: {name}"}

    runner = ProviderRunner(
        provider=provider,
        model=model,
        max_tool_rounds=max_tool_rounds,
        temperature=temperature,
        trace=trace,
    )

    system_prompt = make_system_prompt()
    user_prompt = build_user_prompt(
        question_data=question_data,
        repo_root=repo_root,
        instance_dir=instance_dir,
        instance_files_preview=instance_files,
    )

    template = question_data.get("template_answer", {})
    raw_response = runner.run(system_prompt=system_prompt, user_prompt=user_prompt, tool_callback=tool_callback)
    if trace:
        trace(f"[final-raw] {raw_response}")
    parsed = extract_first_json_object(raw_response)

    coercion_notes: List[str] = []

    def _apply_coercion() -> None:
        nonlocal parsed
        if parsed is None:
            return
        coerced, notes = coerce_against_template(parsed, template)
        parsed = coerced
        if not notes:
            return
        remaining = 200 - len(coercion_notes)
        if remaining > 0:
            coercion_notes.extend(notes[:remaining])
        if trace:
            preview = "; ".join(notes[:12])
            if len(notes) > 12:
                preview += "; ..."
            trace(f"[coerce] {preview}")

    _apply_coercion()

    repair_messages: List[str] = []
    repair_attempts = 0
    while repair_attempts < max_repair_rounds:
        if parsed is None:
            err = "Model response was not valid JSON."
        else:
            errs = validate_against_template(parsed, template)
            if not errs:
                break
            err = "Template validation failed: " + "; ".join(errs)

        repair_attempts += 1
        repair_prompt = (
            f"Your previous answer was invalid.\n"
            f"Error: {err}\n"
            f"Return ONLY one valid JSON object matching this template:\n"
            f"{json.dumps(template, sort_keys=True, separators=(',', ':'))}"
        )
        repair_messages.append(err)

        raw_response = runner.run(
            system_prompt=system_prompt,
            user_prompt=repair_prompt,
            tool_callback=tool_callback,
        )
        parsed = extract_first_json_object(raw_response)
        _apply_coercion()

    if parsed is None:
        raise RuntimeError("Could not extract valid JSON from model response")

    final_errors = validate_against_template(parsed, template)
    if final_errors:
        raise RuntimeError("Final answer failed template validation: " + "; ".join(final_errors))

    usage = runner.usage_summary()
    cost = compute_usage_cost_for_model(provider=provider, model=model, usage=usage)

    debug = {
        "question_path": str(question_path),
        "repair_attempts": repair_attempts,
        "repair_errors": repair_messages,
        "coercion_note_count": len(coercion_notes),
        "coercion_notes": coercion_notes,
        "usage": usage,
        "cost": cost,
        "raw_response": raw_response,
    }
    return parsed, debug


def detect_repo_root(container_workdir: Path, explicit_repo_root: Optional[str], sample_question_text: str) -> Path:
    if explicit_repo_root:
        p = Path(explicit_repo_root)
        if not p.is_absolute():
            p = container_workdir / p
        return p.resolve()

    # Prefer /testbed itself when it looks like a repo checkout.
    if (container_workdir / ".git").exists() or (container_workdir / "pyproject.toml").exists():
        return container_workdir.resolve()

    # Try to infer /testbed/<repo-subdir>/... from question text.
    m = re.search(r"(/testbed/[A-Za-z0-9_.-]+/)", sample_question_text)
    if m:
        inferred = Path(m.group(1)).resolve()
        if inferred.exists() and (
            (inferred / ".git").exists() or (inferred / "pyproject.toml").exists()
        ):
            return inferred

    # Else use /testbed by default.
    return container_workdir.resolve()


def worker_main(args: argparse.Namespace) -> int:
    repo_instances_root = Path(args.instances_root).resolve() / args.repo_name
    if not repo_instances_root.exists():
        raise SystemExit(f"Missing repo instances dir: {repo_instances_root}")

    instance_ids = select_instances(repo_instances_root, args.num_instances)
    if not instance_ids:
        print(f"[{args.repo_name}] No instances selected")
        return 0

    first_q = load_json(repo_instances_root / instance_ids[0] / "question.json")
    repo_root = detect_repo_root(
        container_workdir=Path(args.container_workdir).resolve(),
        explicit_repo_root=args.repo_root,
        sample_question_text=str(first_q.get("question", "")),
    )

    out_repo_root = Path(args.output_repo_root).resolve()
    out_repo_root.mkdir(parents=True, exist_ok=True)

    print(f"[worker] provider={args.provider} model={args.model}")
    print(f"[worker] repo={args.repo_name} repo_root={repo_root}")
    print(f"[worker] instances={len(instance_ids)} output={out_repo_root}")

    for idx, instance_id in enumerate(instance_ids, start=1):
        qpath = repo_instances_root / instance_id / "question.json"
        out_dir = out_repo_root / instance_id
        out_dir.mkdir(parents=True, exist_ok=True)
        answer_path = out_dir / "answer.json"
        log_path = out_dir / "llm.log"
        usage_path = out_dir / "usage.json"

        print(f"[worker][{idx}/{len(instance_ids)}] {instance_id}")

        try:
            answer, debug = run_single_instance(
                provider=args.provider,
                model=args.model,
                question_path=qpath,
                repo_root=repo_root,
                repomap_tokens=args.repomap_tokens,
                max_tool_rounds=args.max_tool_rounds,
                max_read_lines=args.max_read_lines,
                max_read_chars=args.max_read_chars,
                temperature=args.temperature,
                max_repair_rounds=args.max_repair_rounds,
            )
            dump_json(answer_path, answer)
            usage_payload = {
                "status": "ok",
                "instance": instance_id,
                "provider": args.provider,
                "model": args.model,
                "usage": debug.get("usage", empty_usage(args.provider, args.model)),
                "cost": debug.get(
                    "cost",
                    compute_usage_cost_for_model(
                        provider=args.provider,
                        model=args.model,
                        usage=empty_usage(args.provider, args.model),
                    ),
                ),
            }
            dump_json(usage_path, usage_payload)
            log_path.write_text(
                json.dumps(
                    {
                        "status": "ok",
                        "instance": instance_id,
                        "debug": debug,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        except Exception as exc:
            err_payload = {
                "status": "error",
                "instance": instance_id,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
            log_path.write_text(json.dumps(err_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            dump_json(
                usage_path,
                {
                    "status": "error",
                    "instance": instance_id,
                    "provider": args.provider,
                    "model": args.model,
                    "usage": empty_usage(args.provider, args.model),
                    "cost": compute_usage_cost_for_model(
                        provider=args.provider,
                        model=args.model,
                        usage=empty_usage(args.provider, args.model),
                    ),
                    "error": str(exc),
                },
            )
            # Do not write malformed answer.json on errors.

    write_repo_usage_file(out_repo_root, args.provider, args.model)
    return 0


# ---------------------------
# Host mode
# ---------------------------


def require_command(name: str) -> None:
    if subprocess.run(["bash", "-lc", f"command -v {shlex.quote(name)} >/dev/null 2>&1"]).returncode != 0:
        raise SystemExit(f"Required command not found: {name}")


def host_main(args: argparse.Namespace) -> int:
    require_command("docker")

    repos_file = Path(args.repos_file).resolve()
    if not repos_file.exists():
        raise SystemExit(f"Repos file not found: {repos_file}")

    instances_root = Path(args.instances_root).resolve()
    if not instances_root.exists():
        raise SystemExit(f"Instances root not found: {instances_root}")

    repos_map = load_json(repos_file)
    if not isinstance(repos_map, dict) or not repos_map:
        raise SystemExit(f"Invalid repo mapping in {repos_file}")

    all_repos = sorted(repos_map.keys())
    if args.repo == "all":
        target_repos = all_repos
    else:
        if args.repo not in repos_map:
            raise SystemExit(f"Repo '{args.repo}' not found in {repos_file}. Available: {all_repos}")
        target_repos = [args.repo]

    model_segment = sanitize_name(args.model)
    host_model_root = Path(args.output_root).resolve() / "llm" / args.provider / model_segment
    host_model_root.mkdir(parents=True, exist_ok=True)

    script_self = Path(__file__).resolve()

    print(f"Provider:            {args.provider}")
    print(f"Model:               {args.model}")
    print(f"Output root:         {host_model_root}")
    print(f"Target repos:        {' '.join(target_repos)}")
    print(f"Instances root:      {instances_root}")
    print(f"Container workdir:   {args.container_workdir}")
    print()

    for repo in target_repos:
        image = repos_map.get(repo)
        if not image:
            print(f"[{repo}] Skipping: no image configured")
            continue

        host_repo_instances = instances_root / repo
        if not host_repo_instances.exists():
            print(f"[{repo}] Skipping: missing instances dir {host_repo_instances}")
            continue

        selected = select_instances(host_repo_instances, args.num_instances)
        if not selected:
            print(f"[{repo}] Skipping: no instances selected")
            continue

        container_name = f"llm-repomap-{repo.lower()}-{args.provider}-{model_segment}-{os.getpid()}"
        container_workdir = Path(args.container_workdir)
        container_instances_root = container_workdir / "qa_instances_eval"
        container_repo_out = container_workdir / "evaluations" / "llm" / args.provider / model_segment / repo
        host_repo_out = host_model_root / repo
        host_repo_out.mkdir(parents=True, exist_ok=True)

        print(f"[{repo}] Image: {image}")
        run_checked(["docker", "pull", image])

        print(f"[{repo}] Starting container: {container_name}")
        run_checked(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "-w",
                args.container_workdir,
                image,
                "tail",
                "-f",
                "/dev/null",
            ]
        )

        try:
            run_checked(
                [
                    "docker",
                    "exec",
                    container_name,
                    "bash",
                    "-lc",
                    f"mkdir -p {shlex.quote(str(container_instances_root))} {shlex.quote(str(container_repo_out))}",
                ]
            )
            run_checked(["docker", "cp", str(host_repo_instances), f"{container_name}:{container_instances_root}/"])
            run_checked(["docker", "cp", str(script_self), f"{container_name}:{container_workdir}/run_llm_repomap_eval_in_docker.py"])

            if args.install_deps:
                print(f"[{repo}] Ensuring Python deps in container...")
                dep_script = "\n".join(
                    [
                        "import importlib.util, os, subprocess, sys",
                        "provider = os.environ.get('LLM_PROVIDER','')",
                        "os.environ.setdefault('PIP_DISABLE_PIP_VERSION_CHECK', '1')",
                        "wanted = [('aider-chat','aider')]",
                        "if provider == 'openai': wanted.append(('openai','openai'))",
                        "elif provider == 'gemini': wanted.append(('google-genai','google.genai'))",
                        "elif provider == 'anthropic': wanted.append(('anthropic','anthropic'))",
                        "def install_pkg(pkg):",
                        "    subprocess.check_call([sys.executable,'-m','pip','install','--quiet',pkg])",
                        "for pkg, mod in wanted:",
                        "    if importlib.util.find_spec(mod) is not None:",
                        "        continue",
                        "    if pkg == 'aider-chat':",
                        "        try:",
                        "            install_pkg('aider-chat')",
                        "        except subprocess.CalledProcessError:",
                        "            if sys.version_info < (3, 9):",
                        "                install_pkg('aider-chat==0.12.0')",
                        "            else:",
                        "                raise",
                        "    else:",
                        "        install_pkg(pkg)",
                        "print('deps_ok', [p for p, _m in wanted])",
                    ]
                )
                run_checked(
                    [
                        "docker",
                        "exec",
                        "-e",
                        f"LLM_PROVIDER={args.provider}",
                        container_name,
                        "python",
                        "-c",
                        dep_script,
                    ]
                )

            env_args: List[str] = []
            for key in ["OPENAI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"]:
                val = os.environ.get(key)
                if val:
                    env_args.extend(["-e", f"{key}={val}"])

            print(f"[{repo}] Running worker for {len(selected)} instances...")
            worker_cmd = [
                "docker",
                "exec",
                *env_args,
                container_name,
                "python",
                str(container_workdir / "run_llm_repomap_eval_in_docker.py"),
                "--worker",
                "--provider",
                args.provider,
                "--model",
                args.model,
                "--repo-name",
                repo,
                "--instances-root",
                str(container_instances_root),
                "--num-instances",
                str(len(selected)),
                "--output-repo-root",
                str(container_repo_out),
                "--container-workdir",
                str(container_workdir),
                "--max-tool-rounds",
                str(args.max_tool_rounds),
                "--repomap-tokens",
                str(args.repomap_tokens),
                "--max-read-lines",
                str(args.max_read_lines),
                "--max-read-chars",
                str(args.max_read_chars),
                "--temperature",
                str(args.temperature),
                "--max-repair-rounds",
                str(args.max_repair_rounds),
            ]
            if args.repo_root:
                worker_cmd.extend(["--repo-root", args.repo_root])
            run_checked(worker_cmd)

            run_checked(["docker", "cp", f"{container_name}:{container_repo_out}/.", str(host_repo_out)])
            print(f"[{repo}] Copied outputs to: {host_repo_out}")

        finally:
            run_checked(["docker", "rm", "-f", container_name])

    print()
    print(f"Done. Outputs at: {host_model_root}")
    return 0


# ---------------------------
# CLI
# ---------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run read-only QA eval with LLM tool-calling + aider RepoMap in docker."
    )

    p.add_argument("--worker", action="store_true", help="Run worker mode inside container")

    p.add_argument("--provider", choices=["openai", "gemini", "anthropic"], required=True)
    p.add_argument("--model", required=True)

    # Host mode args
    p.add_argument("--repo", default="all", help="Repo key from Repositories.json, or all")
    p.add_argument("--repos-file", default=str(REPO_ROOT / "Repositories.json"))
    p.add_argument("--instances-root", default=str(REPO_ROOT / "qa_instances_eval"))
    p.add_argument("--output-root", default=str(REPO_ROOT / "evaluations"))
    p.add_argument("--container-workdir", default="/testbed")
    p.add_argument("--install-deps", action="store_true", default=False)
    p.add_argument("--num-instances", default="all", help="all or integer limit")

    # Worker mode args
    p.add_argument("--repo-name", default="")
    p.add_argument("--output-repo-root", default="")
    p.add_argument("--repo-root", default="", help="Explicit repo root inside container (default auto-detect)")

    # Shared runtime args
    p.add_argument("--max-tool-rounds", type=int, default=24)
    p.add_argument("--repomap-tokens", type=int, default=6144)
    p.add_argument("--max-read-lines", type=int, default=300)
    p.add_argument("--max-read-chars", type=int, default=90000)
    p.add_argument("--max-repair-rounds", type=int, default=2)
    p.add_argument("--temperature", type=float, default=0.0)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.num_instances != "all":
        try:
            n = int(args.num_instances)
        except ValueError as exc:
            raise SystemExit("--num-instances must be 'all' or an integer") from exc
        if n < 0:
            raise SystemExit("--num-instances must be >= 0")

    if args.worker:
        if not args.repo_name:
            raise SystemExit("--repo-name is required in --worker mode")
        if not args.output_repo_root:
            raise SystemExit("--output-repo-root is required in --worker mode")
        return worker_main(args)

    raise SystemExit(
        "Direct docker orchestration mode is disabled. "
        "Use evaluation_scripts/run_llm_repomap_eval_host.py for host-side runs."
    )


if __name__ == "__main__":
    raise SystemExit(main())
