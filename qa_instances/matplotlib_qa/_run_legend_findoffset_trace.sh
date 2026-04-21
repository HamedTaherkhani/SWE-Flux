#!/usr/bin/env bash
# One-shot: SWE matplotlib image + trace Legend._findoffset returns + pytest legend test.
set -euo pipefail
REPO="${REPO:-/home/mohammad/fun/RepoBehave}"
IMAGE="${IMAGE:-starryzhang/sweb.eval.x86_64.matplotlib_1776_matplotlib-29209:latest}"
docker run --rm \
  -v "${REPO}:/repo" \
  -w /testbed \
  "${IMAGE}" \
  bash -lc '
set -e
export PYTHONPATH=/testbed/lib
cp /repo/qa_instances/matplotlib_qa/shared/files/tests/qa/trace_plugin.py /testbed/trace_plugin.py
cp /repo/qa_instances/matplotlib_qa/shared/files/tests/qa/conftest.py /testbed/conftest.py
mkdir -p /testbed/tests/qa
cp /repo/qa_instances/matplotlib_qa/legend_bbox_anchor_offset_state_deep/files/tests/qa/legend_bbox_anchor_offset_state_deep_test.py /testbed/tests/qa/
export TRACE_ON=1
export TRACE_FILE=matplotlib/legend
export TRACE_FUNC=Legend._findoffset
export TRACE_EVENTS=return
export TRACE_OUT=/tmp/t.log
export TRACE_LIMIT=200000
export TRACE_MAXLOCALS=80
export TRACE_FULL_LOCALS_ON_RETURN=1
rm -f /tmp/t.log
cd /testbed
python -m pytest -s tests/qa/legend_bbox_anchor_offset_state_deep_test.py -k legend_bbox 2>&1 | tail -5
echo "---TRACE LAST---"
grep _findoffset /tmp/t.log | tail -1 | tee /repo/qa_instances/matplotlib_qa/_docker_legend_last_findoffset.txt
'
