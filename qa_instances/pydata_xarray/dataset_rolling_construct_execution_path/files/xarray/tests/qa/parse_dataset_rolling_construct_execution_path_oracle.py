#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

EVENT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} .*? "
    r"(?P<path>[^:]+):(?P<lineno>\d+) "
    r"(?P<func>[^ ]+) "
    r"event=(?P<event>call|line|return|exception)\b",
)

TARGET_FILE = "xarray/computation/rolling.py"
TARGET_FUNC_IDENTIFIER = (
    "xarray.computation.rolling.construct|||"
    "xarray/computation/rolling.py::DatasetRolling.construct|||"
    "DatasetRolling.construct|||construct"
)


def _normalize_path(path: str) -> str:
    return path.replace('\\', '/')


def _short_name(func_token: str) -> str:
    rhs = func_token.split('::', 1)[-1]
    return rhs.rsplit('.', 1)[-1]


def _parse_locals(line: str) -> dict[str, str]:
    marker = ' locals='
    idx = line.find(marker)
    if idx == -1:
        return {}
    return ast.literal_eval(line[idx + len(marker):])


def _construct_frame_kind(locals_map: dict[str, str]) -> str:
    self_repr = locals_map.get('self', '')
    if 'DatasetRolling [' in self_repr:
        return 'dataset'
    if 'DataArrayRolling [' in self_repr:
        return 'dataarray'
    return 'other'


def extract_execution_path(trace_text: str) -> dict[str, list[dict[str, int | str]]]:
    construct_stack: list[str] = []
    path: list[dict[str, int | str]] = []

    for raw_line in trace_text.splitlines():
        m = EVENT_RE.match(raw_line)
        if m is None:
            continue

        event = m.group('event')
        func = m.group('func')
        lineno = int(m.group('lineno'))
        path_value = _normalize_path(m.group('path'))

        if not path_value.endswith('/' + TARGET_FILE):
            continue
        if _short_name(func) != 'construct':
            continue

        if event == 'call':
            construct_stack.append(_construct_frame_kind(_parse_locals(raw_line)))
            continue

        if event in {'return', 'exception'}:
            if construct_stack:
                construct_stack.pop()
            continue

        if construct_stack and construct_stack[-1] == 'dataset':
            path.append(
                {
                    'file': TARGET_FILE,
                    'func': TARGET_FUNC_IDENTIFIER,
                    'line': lineno,
                }
            )

    if not path:
        raise ValueError('Could not find DatasetRolling.construct line events in trace log.')

    return {'executed_path': path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--trace-log',
        default='/testbed/logs/qa_instances/dataset_rolling_construct_execution_path/trace.log',
    )
    parser.add_argument(
        '--out',
        default='/testbed/logs/qa_instances/dataset_rolling_construct_execution_path/oracle.json',
    )
    args = parser.parse_args()

    trace_text = Path(args.trace_log).read_text(encoding='utf-8')
    output = extract_execution_path(trace_text)

    qa = {
        'question_kind': 'C1_IntraProceduralCFG',
        'question': (
            'Use `xarray/tests/qa/dataset_rolling_construct_execution_path_test.py`, class '
            '`TestDatasetRollingConstructExecutionPathHardQA`, method '
            '`test_dataset_rolling_construct_execution_path_case`. '
            "At line 31, `ds.rolling(x=3, center=True).construct(window_dim='win', stride=2, "
            "fill_value=-1, keep_attrs=False)` is called. Focus only on "
            '`xarray/computation/rolling.py::DatasetRolling.construct` itself. '
            'Do not include nested executions of `DataArrayRolling.construct` or `_construct`. '
            'What is the exact ordered execution path inside `DatasetRolling.construct`, including '
            'repeated line visits from loop iterations and branch checks? Return it as '
            '`executed_path`, a list of objects with keys `file`, `func`, and `line`.'
        ),
        'template_answer': {
            'executed_path': [
                {'file': 'str', 'func': 'str', 'line': 'int'}
            ]
        },
        'oracle_answer': output,
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(qa, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
