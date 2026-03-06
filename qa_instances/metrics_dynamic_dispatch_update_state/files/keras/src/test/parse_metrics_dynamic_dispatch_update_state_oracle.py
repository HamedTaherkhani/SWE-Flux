#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? (/testbed/keras/src/[^:]+):(\d+) ([^ ]+) event=(call|return|exception) ",
    re.MULTILINE,
)

DISPATCH_CALLSITE_FUNC = "keras.src.metrics.metric.__call__"
DISPATCH_CALLSITE_FILE = "keras/src/metrics/metric.py"
DISPATCH_CALLSITE_LINE = 225


def extract_dispatched_update_state(trace_text: str):
    events = [
        {
            "file": file_path.replace("/testbed/", ""),
            "line": int(line_no),
            "func": func,
            "event": event,
        }
        for file_path, line_no, func, event in EVENT_RE.findall(trace_text)
    ]
    if not events:
        raise ValueError("No events found in trace log.")

    for i, ev in enumerate(events):
        if (
            ev["event"] == "call"
            and ev["file"] == DISPATCH_CALLSITE_FILE
            and ev["func"] == DISPATCH_CALLSITE_FUNC
        ):
            for nxt in events[i + 1 :]:
                if nxt["event"] != "call":
                    continue
                if nxt["func"].endswith(".update_state") and not nxt["file"].endswith(
                    "metric.py"
                ):
                    concrete_class = "MeanMetricWrapper"
                    if nxt["file"].endswith("accuracy_metrics.py"):
                        concrete_class = "BinaryAccuracy"
                    return {
                        "dispatched_function": nxt["func"],
                        "dispatched_file": nxt["file"],
                        "concrete_class": concrete_class,
                    }
    raise ValueError("Could not find dispatched concrete update_state call.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trace-log",
        default="/testbed/logs/qa_instances/metrics_dynamic_dispatch_update_state/trace.log",
    )
    parser.add_argument(
        "--out",
        default="/testbed/logs/qa_instances/metrics_dynamic_dispatch_update_state/oracle.json",
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding="utf-8")
    dispatched = extract_dispatched_update_state(trace_text)

    qa = {
        "question_kind": "dynamic_dispatch",
        "question": (
            "Use `keras/src/test/metrics/metrics_dynamic_dispatch_update_state_test.py`, "
            "class `MetricsDynamicDispatchUpdateStateQATest`, method "
            "`test_concrete_update_state_dispatched_from_metric_call`. Setup: "
            "construct `BinaryAccuracy(name='dispatch_binary_acc', threshold=0.35)`, "
            "then call `metric(y_true, y_pred, sample_weight=...)` followed by "
            "`metric(y_true, y_pred)` using the exact arrays in the test. In "
            "`keras/src/metrics/metric.py` at line 225 inside `Metric.__call__`, "
            "the code calls `self.update_state(...)`. Which concrete class's "
            "`update_state` implementation was actually executed for that dispatch?"
        ),
        "oracle_answer": {
            "dispatch_callsite": {
                "file": DISPATCH_CALLSITE_FILE,
                "line": DISPATCH_CALLSITE_LINE,
                "func": DISPATCH_CALLSITE_FUNC,
            },
            **dispatched,
        },
    }

    Path(args.out).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
