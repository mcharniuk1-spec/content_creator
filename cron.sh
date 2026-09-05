#!/usr/bin/env bash
# Pinned local worker only. Existing scheduler installation is not changed by Git.
set -euo pipefail
: "${M2_RUN_CONFIG:?Set M2_RUN_CONFIG to a private explicit run configuration}"
M2_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$M2_ROOT"
M2_PYTHON="${M2_PYTHON:-python3}"
exec "$M2_PYTHON" server_entry.py --config "$M2_RUN_CONFIG"
