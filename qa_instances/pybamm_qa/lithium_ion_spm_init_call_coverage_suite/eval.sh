#!/bin/bash
set -euo pipefail
ROOT_DIR="${1:-/testbed}"; ID="lithium_ion_spm_init_call_coverage_suite"; LOG="$ROOT_DIR/logs/qa_instances/$ID"
mkdir -p "$LOG"; cd "$ROOT_DIR"
export TRACE_ON=1 TRACE_FILE="/testbed/src/pybamm/" TRACE_FUNC="pybamm.models.full_battery_models,pybamm.models.base_model,pybamm.models.submodels.particle,pybamm.models.submodels.interface,pybamm.models.submodels.thermal,pybamm.citations"
export TRACE_EVENTS="call,return,exception" TRACE_OUT="$LOG/trace.log" TRACE_LIMIT=0 TRACE_MAXLOCALS=1 TRACE_FULL_LOCALS_ON_RETURN=0 PYBAMM_DISABLE_TELEMETRY=true
rm -f "$LOG/trace.log" "$LOG/pytest.log" "$LOG/oracle.log" "$LOG/oracle.json"
pytest -n 0 -rA -s tests/qa/lithium_ion_spm_init_call_coverage_suite_test.py 2>&1 | tee "$LOG/pytest.log"
python tests/qa/parse_lithium_ion_spm_init_call_coverage_suite_oracle.py --trace-log "$LOG/trace.log" --out "$LOG/oracle.json" | tee "$LOG/oracle.log"
