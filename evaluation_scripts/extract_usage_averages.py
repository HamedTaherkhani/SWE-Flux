#!/usr/bin/env python3
"""Aggregate evaluation usage averages by tool/llm/instance."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class UsageObservation:
    tool: str
    llm: str
    repo: str
    instance: str
    source: str
    total_tokens: float | None = None
    input_tokens: float | None = None
    output_tokens: float | None = None
    cached_input_tokens: float | None = None
    cache_creation_input_tokens: float | None = None
    cost_usd: float | None = None


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    lower = text.lower()
    if lower in {"included", "n/a", "na", "none", "null", "nan"}:
        return None
    if text.startswith("$"):
        text = text[1:]
    try:
        return float(text)
    except ValueError:
        return None


def _parse_iso_to_epoch_ms(value: str | None) -> int | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return int(dt.timestamp() * 1000)


def _extract_max_timestamp_ms(traj_path: Path) -> int | None:
    try:
        payload = _load_json(traj_path)
    except Exception:
        return None
    events = payload.get("events")
    if not isinstance(events, list):
        return None
    max_ts: int | None = None
    for event in events:
        if not isinstance(event, dict):
            continue
        ts = _to_float(event.get("timestamp_ms"))
        if ts is None:
            continue
        ts_i = int(ts)
        if max_ts is None or ts_i > max_ts:
            max_ts = ts_i
    return max_ts


def _avg(values: list[float | None]) -> tuple[float | None, int]:
    clean = [v for v in values if v is not None]
    if not clean:
        return None, 0
    return sum(clean) / len(clean), len(clean)


def _format_num(value: float | None, decimals: int = 6) -> str:
    if value is None:
        return ""
    return f"{value:.{decimals}f}"


def _resolve_cursor_model_pricing(
    model_name: str, pricing_db: dict[str, Any]
) -> dict[str, Any] | None:
    models = pricing_db.get("models")
    if not isinstance(models, dict):
        return None
    seen: set[str] = set()
    current = model_name
    while True:
        if current in seen:
            return None
        seen.add(current)
        entry = models.get(current)
        if not isinstance(entry, dict):
            return None
        alias = entry.get("alias_of")
        if isinstance(alias, str) and alias:
            current = alias
            continue
        return entry


def _compute_cursor_cost_from_row(
    row: dict[str, Any], pricing_db: dict[str, Any]
) -> float | None:
    model_name = str(row.get("Model") or "").strip()
    if not model_name:
        return None
    model_pricing = _resolve_cursor_model_pricing(model_name, pricing_db)
    if not model_pricing:
        return None

    uncached_input_rate = _to_float(model_pricing.get("input_uncached_cost_per_1m"))
    cache_write_rate = _to_float(model_pricing.get("cache_write_input_cost_per_1m"))
    cache_read_rate = _to_float(model_pricing.get("cache_read_input_cost_per_1m"))
    output_rate = _to_float(model_pricing.get("output_cost_per_1m"))
    if uncached_input_rate is None or output_rate is None:
        return None
    if cache_write_rate is None:
        cache_write_rate = uncached_input_rate
    if cache_read_rate is None:
        cache_read_rate = uncached_input_rate

    token_fee = _to_float(pricing_db.get("cursor_token_fee_per_1m")) or 0.0
    apply_token_fee = bool(pricing_db.get("apply_token_fee_to_all_tokens", True))

    uncached_input_tokens = _to_float(row.get("Input (w/o Cache Write)")) or 0.0
    cache_write_tokens = _to_float(row.get("Input (w/ Cache Write)")) or 0.0
    cache_read_tokens = _to_float(row.get("Cache Read")) or 0.0
    output_tokens = _to_float(row.get("Output Tokens")) or 0.0

    uncached_eff = uncached_input_rate + (token_fee if apply_token_fee else 0.0)
    cache_write_eff = cache_write_rate + (token_fee if apply_token_fee else 0.0)
    cache_read_eff = cache_read_rate + (token_fee if apply_token_fee else 0.0)
    output_eff = output_rate + (token_fee if apply_token_fee else 0.0)

    return (
        (uncached_input_tokens / 1_000_000.0) * uncached_eff
        + (cache_write_tokens / 1_000_000.0) * cache_write_eff
        + (cache_read_tokens / 1_000_000.0) * cache_read_eff
        + (output_tokens / 1_000_000.0) * output_eff
    )


def _match_cursor_rows_to_instances(
    instance_timestamps: dict[str, int | None],
    row_timestamps: list[int | None],
) -> dict[str, int]:
    instances = list(instance_timestamps.keys())
    pairs: list[tuple[int, int, int]] = []
    for i, inst_name in enumerate(instances):
        inst_ts = instance_timestamps[inst_name]
        if inst_ts is None:
            continue
        for row_idx, row_ts in enumerate(row_timestamps):
            if row_ts is None:
                continue
            pairs.append((abs(inst_ts - row_ts), i, row_idx))

    pairs.sort(key=lambda t: t[0])
    assigned_inst: set[int] = set()
    assigned_rows: set[int] = set()
    mapping: dict[str, int] = {}

    for _dist, inst_i, row_i in pairs:
        if inst_i in assigned_inst or row_i in assigned_rows:
            continue
        assigned_inst.add(inst_i)
        assigned_rows.add(row_i)
        mapping[instances[inst_i]] = row_i

    remaining_instances = [idx for idx in range(len(instances)) if idx not in assigned_inst]
    remaining_rows = [idx for idx in range(len(row_timestamps)) if idx not in assigned_rows]
    for inst_i, row_i in zip(remaining_instances, remaining_rows):
        mapping[instances[inst_i]] = row_i

    return mapping


def collect_cursor_observations(
    tool_root: Path, pricing_db: dict[str, Any] | None = None
) -> list[UsageObservation]:
    pricing_db = pricing_db or {}
    out: list[UsageObservation] = []
    for llm_dir in sorted(p for p in tool_root.iterdir() if p.is_dir()):
        llm_name = llm_dir.name
        for repo_dir in sorted(p for p in llm_dir.iterdir() if p.is_dir()):
            instance_dirs = sorted(
                p for p in repo_dir.iterdir() if p.is_dir() and (p / "traj.json").exists()
            )
            if not instance_dirs:
                continue

            instance_ts: dict[str, int | None] = {}
            for inst_dir in instance_dirs:
                ts = _extract_max_timestamp_ms(inst_dir / "traj.json")
                instance_ts[inst_dir.name] = ts

            usage_rows: list[dict[str, Any]] = []
            row_ts: list[int | None] = []
            usage_csv = repo_dir / "usage.csv"
            if usage_csv.exists():
                with usage_csv.open("r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        usage_rows.append(row)
                        row_ts.append(_parse_iso_to_epoch_ms(row.get("Date")))

            mapping: dict[str, int] = {}
            if usage_rows:
                mapping = _match_cursor_rows_to_instances(instance_ts, row_ts)

            # Always include every usage.csv row (this is the canonical Cursor usage source).
            if usage_rows:
                row_to_instance: dict[int, str] = {v: k for k, v in mapping.items()}
                for row_idx, row in enumerate(usage_rows):
                    instance_name = row_to_instance.get(row_idx, f"csv_row_{row_idx + 1}")
                    obs = UsageObservation(
                        tool="cursor",
                        llm=llm_name,
                        repo=repo_dir.name,
                        instance=instance_name,
                        source="usage.csv",
                    )
                    in_cache_write = _to_float(row.get("Input (w/ Cache Write)"))
                    in_no_cache_write = _to_float(row.get("Input (w/o Cache Write)"))
                    cache_read = _to_float(row.get("Cache Read"))
                    out_tokens = _to_float(row.get("Output Tokens"))
                    obs.input_tokens = (
                        (in_cache_write or 0.0) + (in_no_cache_write or 0.0)
                        if in_cache_write is not None or in_no_cache_write is not None
                        else None
                    )
                    obs.cache_creation_input_tokens = in_cache_write
                    obs.cached_input_tokens = cache_read
                    obs.output_tokens = out_tokens
                    obs.total_tokens = _to_float(row.get("Total Tokens"))
                    computed_cost = _compute_cursor_cost_from_row(row, pricing_db)
                    obs.cost_usd = computed_cost
                    if obs.cost_usd is None:
                        obs.cost_usd = _to_float(row.get("Cost"))
                    out.append(obs)
                continue

            # If usage.csv is missing, preserve instance placeholders for visibility.
            for inst_dir in instance_dirs:
                out.append(
                    UsageObservation(
                        tool="cursor",
                        llm=llm_name,
                        repo=repo_dir.name,
                        instance=inst_dir.name,
                        source="usage.csv",
                    )
                )
    return out


def _parse_claude_result_usage(result_event: dict[str, Any]) -> tuple[dict[str, float | None], float | None]:
    usage = result_event.get("usage")
    input_tokens: float | None = None
    output_tokens: float | None = None
    cache_read: float | None = None
    cache_creation: float | None = None

    if isinstance(usage, dict):
        input_tokens = _to_float(usage.get("input_tokens"))
        output_tokens = _to_float(usage.get("output_tokens"))
        cache_read = _to_float(usage.get("cache_read_input_tokens"))
        cache_creation = _to_float(usage.get("cache_creation_input_tokens"))

    if input_tokens is None and output_tokens is None:
        model_usage = result_event.get("modelUsage")
        if isinstance(model_usage, dict) and model_usage:
            model_values = next(iter(model_usage.values()))
            if isinstance(model_values, dict):
                input_tokens = _to_float(model_values.get("inputTokens"))
                output_tokens = _to_float(model_values.get("outputTokens"))
                cache_read = _to_float(model_values.get("cacheReadInputTokens"))
                cache_creation = _to_float(model_values.get("cacheCreationInputTokens"))

    total_tokens = None
    parts = [input_tokens, output_tokens, cache_read, cache_creation]
    if any(v is not None for v in parts):
        total_tokens = sum(v or 0.0 for v in parts)

    cost = _to_float(result_event.get("total_cost_usd"))
    if cost is None:
        model_usage = result_event.get("modelUsage")
        if isinstance(model_usage, dict) and model_usage:
            model_values = next(iter(model_usage.values()))
            if isinstance(model_values, dict):
                cost = _to_float(model_values.get("costUSD"))

    return (
        {
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_input_tokens": cache_read,
            "cache_creation_input_tokens": cache_creation,
        },
        cost,
    )


def collect_claude_observations(tool_root: Path) -> list[UsageObservation]:
    out: list[UsageObservation] = []
    for llm_dir in sorted(p for p in tool_root.iterdir() if p.is_dir()):
        llm_name = llm_dir.name
        for repo_dir in sorted(p for p in llm_dir.iterdir() if p.is_dir()):
            for inst_dir in sorted(p for p in repo_dir.iterdir() if p.is_dir()):
                traj_path = inst_dir / "traj.json"
                obs = UsageObservation(
                    tool="claude_code",
                    llm=llm_name,
                    repo=repo_dir.name,
                    instance=inst_dir.name,
                    source="traj.json",
                )
                if traj_path.exists():
                    try:
                        payload = _load_json(traj_path)
                        events = payload.get("events")
                        if isinstance(events, list):
                            result_events = [
                                e
                                for e in events
                                if isinstance(e, dict)
                                and e.get("type") == "result"
                                and e.get("subtype") == "success"
                            ]
                            if result_events:
                                metrics, cost = _parse_claude_result_usage(result_events[-1])
                                obs.total_tokens = metrics["total_tokens"]
                                obs.input_tokens = metrics["input_tokens"]
                                obs.output_tokens = metrics["output_tokens"]
                                obs.cached_input_tokens = metrics["cached_input_tokens"]
                                obs.cache_creation_input_tokens = metrics[
                                    "cache_creation_input_tokens"
                                ]
                                obs.cost_usd = cost
                    except Exception:
                        pass
                out.append(obs)
    return out


def collect_mini_swe_observations(tool_root: Path) -> list[UsageObservation]:
    out: list[UsageObservation] = []
    for llm_dir in sorted(p for p in tool_root.iterdir() if p.is_dir()):
        llm_name = llm_dir.name
        for repo_dir in sorted(p for p in llm_dir.iterdir() if p.is_dir()):
            for inst_dir in sorted(p for p in repo_dir.iterdir() if p.is_dir()):
                traj_path = inst_dir / "mini.traj.json"
                obs = UsageObservation(
                    tool="mini-swe-agent",
                    llm=llm_name,
                    repo=repo_dir.name,
                    instance=inst_dir.name,
                    source="mini.traj.json",
                )
                if traj_path.exists():
                    try:
                        payload = _load_json(traj_path)
                        info = payload.get("info")
                        if isinstance(info, dict):
                            model_stats = info.get("model_stats")
                            if isinstance(model_stats, dict):
                                obs.cost_usd = _to_float(model_stats.get("instance_cost"))

                        total = 0.0
                        input_tokens = 0.0
                        output_tokens = 0.0
                        cached_input_tokens = 0.0
                        saw_usage = False

                        messages = payload.get("messages")
                        if isinstance(messages, list):
                            for message in messages:
                                if not isinstance(message, dict):
                                    continue
                                extra = message.get("extra")
                                if not isinstance(extra, dict):
                                    continue
                                response = extra.get("response")
                                if not isinstance(response, dict):
                                    continue
                                usage = response.get("usage")
                                if not isinstance(usage, dict):
                                    continue
                                saw_usage = True
                                p = _to_float(usage.get("prompt_tokens")) or 0.0
                                c = _to_float(usage.get("completion_tokens")) or 0.0
                                t = _to_float(usage.get("total_tokens"))
                                if t is None:
                                    t = p + c
                                total += t
                                input_tokens += p
                                output_tokens += c

                                prompt_details = usage.get("prompt_tokens_details")
                                if isinstance(prompt_details, dict):
                                    cached_input_tokens += (
                                        _to_float(prompt_details.get("cached_tokens")) or 0.0
                                    )

                        if saw_usage:
                            obs.total_tokens = total
                            obs.input_tokens = input_tokens
                            obs.output_tokens = output_tokens
                            obs.cached_input_tokens = cached_input_tokens
                    except Exception:
                        pass
                out.append(obs)
    return out


def collect_llm_observations(tool_root: Path) -> list[UsageObservation]:
    out: list[UsageObservation] = []
    for provider_dir in sorted(p for p in tool_root.iterdir() if p.is_dir()):
        provider = provider_dir.name
        for model_dir in sorted(p for p in provider_dir.iterdir() if p.is_dir()):
            llm_name = f"{provider}/{model_dir.name}"
            for repo_dir in sorted(p for p in model_dir.iterdir() if p.is_dir()):
                for inst_dir in sorted(p for p in repo_dir.iterdir() if p.is_dir()):
                    obs = UsageObservation(
                        tool="llm",
                        llm=llm_name,
                        repo=repo_dir.name,
                        instance=inst_dir.name,
                        source="usage.json",
                    )
                    usage_path = inst_dir / "usage.json"
                    if usage_path.exists():
                        try:
                            payload = _load_json(usage_path)
                            usage = payload.get("usage")
                            if isinstance(usage, dict):
                                input_tokens = _to_float(usage.get("input_tokens"))
                                output_tokens = _to_float(usage.get("output_tokens"))
                                total_tokens = _to_float(usage.get("total_tokens"))
                                if total_tokens is None and (
                                    input_tokens is not None or output_tokens is not None
                                ):
                                    total_tokens = (input_tokens or 0.0) + (output_tokens or 0.0)
                                obs.total_tokens = total_tokens
                                obs.input_tokens = input_tokens
                                obs.output_tokens = output_tokens
                                obs.cached_input_tokens = _to_float(
                                    usage.get("cached_input_tokens")
                                )
                                obs.cache_creation_input_tokens = _to_float(
                                    usage.get("cache_creation_input_tokens")
                                )

                            cost = payload.get("cost")
                            if isinstance(cost, dict):
                                obs.cost_usd = _to_float(cost.get("cost_usd"))
                        except Exception:
                            pass
                    out.append(obs)
    return out


def collect_all_observations(
    evaluations_root: Path, cursor_pricing_db: dict[str, Any] | None = None
) -> list[UsageObservation]:
    observations: list[UsageObservation] = []
    cursor_root = evaluations_root / "cursor"
    if cursor_root.exists():
        observations.extend(collect_cursor_observations(cursor_root, pricing_db=cursor_pricing_db))
    claude_root = evaluations_root / "claude_code"
    if claude_root.exists():
        observations.extend(collect_claude_observations(claude_root))
    mini_root = evaluations_root / "mini-swe-agent"
    if mini_root.exists():
        observations.extend(collect_mini_swe_observations(mini_root))
    llm_root = evaluations_root / "llm"
    if llm_root.exists():
        observations.extend(collect_llm_observations(llm_root))
    return observations


def write_averages_csv(observations: list[UsageObservation], out_csv: Path) -> int:
    grouped: dict[tuple[str, str], list[UsageObservation]] = defaultdict(list)
    for obs in observations:
        grouped[(obs.tool, obs.llm)].append(obs)

    rows: list[dict[str, str]] = []
    for (tool, llm), items in grouped.items():
        total_avg, total_n = _avg([i.total_tokens for i in items])
        input_avg, input_n = _avg([i.input_tokens for i in items])
        output_avg, output_n = _avg([i.output_tokens for i in items])
        cached_avg, cached_n = _avg([i.cached_input_tokens for i in items])
        cache_create_avg, cache_create_n = _avg([i.cache_creation_input_tokens for i in items])
        cost_avg, cost_n = _avg([i.cost_usd for i in items])
        repos_seen = len({i.repo for i in items})
        repos_with_usage = len(
            {
                i.repo
                for i in items
                if any(
                    v is not None
                    for v in (
                        i.total_tokens,
                        i.input_tokens,
                        i.output_tokens,
                        i.cached_input_tokens,
                        i.cache_creation_input_tokens,
                        i.cost_usd,
                    )
                )
            }
        )
        instances_seen = len({(i.repo, i.instance) for i in items})
        instances_with_usage = len(
            {
                (i.repo, i.instance)
                for i in items
                if any(
                    v is not None
                    for v in (
                        i.total_tokens,
                        i.input_tokens,
                        i.output_tokens,
                        i.cached_input_tokens,
                        i.cache_creation_input_tokens,
                        i.cost_usd,
                    )
                )
            }
        )
        sources = sorted({i.source for i in items if i.source})

        if (
            total_n == 0
            and input_n == 0
            and output_n == 0
            and cached_n == 0
            and cache_create_n == 0
            and cost_n == 0
        ):
            continue

        rows.append(
            {
                "tool": tool,
                "llm": llm,
                "avg_total_tokens": _format_num(total_avg),
                "avg_input_tokens": _format_num(input_avg),
                "avg_output_tokens": _format_num(output_avg),
                "avg_cached_input_tokens": _format_num(cached_avg),
                "avg_cache_creation_input_tokens": _format_num(cache_create_avg),
                "avg_cost_usd": _format_num(cost_avg),
                "token_samples_total": str(total_n),
                "token_samples_input": str(input_n),
                "token_samples_output": str(output_n),
                "token_samples_cached_input": str(cached_n),
                "token_samples_cache_creation": str(cache_create_n),
                "cost_samples": str(cost_n),
                "repos_seen": str(repos_seen),
                "repos_with_usage": str(repos_with_usage),
                "instances_seen": str(instances_seen),
                "instances_with_usage": str(instances_with_usage),
                "source": ";".join(sources),
            }
        )

    rows.sort(key=lambda r: (r["tool"], r["llm"]))
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "tool",
        "llm",
        "avg_total_tokens",
        "avg_input_tokens",
        "avg_output_tokens",
        "avg_cached_input_tokens",
        "avg_cache_creation_input_tokens",
        "avg_cost_usd",
        "token_samples_total",
        "token_samples_input",
        "token_samples_output",
        "token_samples_cached_input",
        "token_samples_cache_creation",
        "cost_samples",
        "repos_seen",
        "repos_with_usage",
        "instances_seen",
        "instances_with_usage",
        "source",
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    default_evaluations_root = repo_root / "evaluations"
    default_output_csv = default_evaluations_root / "usage_averages_by_tool_llm_instance.csv"
    default_cursor_costs_json = default_evaluations_root / "cursor" / "model_token_costs.json"

    parser = argparse.ArgumentParser(
        description="Extract per-instance usage and write tool/llm averages across repos."
    )
    parser.add_argument(
        "--evaluations-root",
        type=Path,
        default=default_evaluations_root,
        help="Path to evaluations root directory.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=default_output_csv,
        help="Output CSV path.",
    )
    parser.add_argument(
        "--cursor-costs-json",
        type=Path,
        default=default_cursor_costs_json,
        help="Cursor model token pricing JSON file.",
    )
    args = parser.parse_args()

    cursor_pricing_db: dict[str, Any] = {}
    if args.cursor_costs_json.exists():
        try:
            payload = _load_json(args.cursor_costs_json)
            if isinstance(payload, dict):
                cursor_pricing_db = payload
        except Exception:
            cursor_pricing_db = {}

    observations = collect_all_observations(
        args.evaluations_root, cursor_pricing_db=cursor_pricing_db
    )
    n_rows = write_averages_csv(observations, args.output_csv)
    print(f"Wrote {n_rows} rows to {args.output_csv}")


if __name__ == "__main__":
    main()
