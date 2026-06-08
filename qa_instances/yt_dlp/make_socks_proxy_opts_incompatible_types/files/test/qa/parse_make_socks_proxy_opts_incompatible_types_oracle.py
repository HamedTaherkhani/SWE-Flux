#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


# Trace plugin records the helper as `<test_module>._probe`. The test module
# name depends on how pytest imports the file, so match by suffix.
RETURN_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>/testbed/test/qa/make_socks_proxy_opts_incompatible_types_test\.py):(?P<lineno>\d+) "
    r"(?P<func>\S*\._probe) "
    r"event=return retval=(?P<retval>.*?) locals=\{.*\}$",
    re.MULTILINE,
)


def extract_snapshots(trace_text: str) -> dict:
    matches = list(RETURN_RE.finditer(trace_text))
    if len(matches) != 3:
        raise ValueError(f"Expected exactly 3 _probe return events, got {len(matches)}.")

    snapshots = {}
    for m in matches:
        snap = ast.literal_eval(m.group("retval"))
        if not isinstance(snap, dict) or "label" not in snap:
            raise ValueError(f"Unexpected snapshot shape: {snap!r}")
        snapshots[snap["label"]] = snap
    return {"probes": snapshots}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/make_socks_proxy_opts_incompatible_types/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/make_socks_proxy_opts_incompatible_types/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    output = extract_snapshots(trace_text)

    qa = {
        "question_kind": "S6_Exceptions",
        "question": (
            "Use `test/qa/make_socks_proxy_opts_incompatible_types_test.py`, class "
            "`TestMakeSocksProxyOptsIncompatibleTypesQA`, method "
            "`test_make_socks_proxy_opts_incompatible_types_case`. "
            "The test invokes the helper "
            "`yt_dlp.networking._helper.make_socks_proxy_opts(socks_proxy)` (defined at "
            "line 54 in `yt_dlp/networking/_helper.py`) THREE times, each via a tiny "
            "`_probe(label, value)` wrapper that runs `make_socks_proxy_opts(value)` and "
            "returns a dict describing the outcome -- either `{label, kind='output', "
            "value_repr}` on success or `{label, kind='exception', exception_type, "
            "exception_message}` on failure. The three labeled probes are: "
            "`'bytes_url'` -> `b'socks5://host:1080'`, "
            "`'int_value'` -> `12345`, and "
            "`'none_value'` -> `None`. "
            "Note: `make_socks_proxy_opts` calls `urllib.parse.urlparse(socks_proxy)` "
            "FIRST, then chains `if/elif` against `url_components.scheme.lower()` for the "
            "literal *str* values `'socks5'`, `'socks5h'`, `'socks4'`, `'socks4a'`, falling "
            "to `else: raise ValueError(f'Unknown SOCKS proxy version: "
            "{url_components.scheme.lower()}')`. CPython's `urlparse` accepts None and "
            "bytes specially (and may yield a *bytes* `scheme` for those inputs), and "
            "raises during decoding when given other non-string types. "
            "Report the outcome dict for each of the three probes. Return a JSON object "
            "with one key `probes` whose value is an object mapping each label to the "
            "exact snapshot dict the helper returned (with all keys and values, "
            "byte-for-byte)."
        ),
        "template_answer": {
            "probes": {
                "bytes_url": {
                    "label": "str",
                    "kind": "str",
                    "exception_type": "str_or_absent",
                    "exception_message": "str_or_absent",
                    "value_repr": "str_or_absent",
                },
                "int_value": {"label": "str", "kind": "str", "...": "..."},
                "none_value": {"label": "str", "kind": "str", "...": "..."},
            },
        },
        "oracle_answer": output,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
