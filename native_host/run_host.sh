#!/usr/bin/env bash
# Native messaging entrypoint — uses the project venv when present.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  exec "$ROOT/.venv/bin/python" "$ROOT/native_host/host.py"
fi
exec python3 "$ROOT/native_host/host.py"
