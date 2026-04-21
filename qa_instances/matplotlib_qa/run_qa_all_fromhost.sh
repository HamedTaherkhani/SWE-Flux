#!/bin/bash
set -euo pipefail

# Same as run_all_qa_fromhost.sh; alternate name for convenience.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$HERE/run_all_qa_fromhost.sh" "$@"
