#!/usr/bin/env bash
# Native messaging entrypoint — Chrome/Firefox often spawn us with no DISPLAY.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Restore a graphical session so tkinter dialogs can appear.
if [[ -z "${DISPLAY:-}" ]]; then
  if [[ -S /tmp/.X11-unix/X0 ]]; then
    export DISPLAY=":0"
  elif [[ -d /tmp/.X11-unix ]]; then
    first="$(ls /tmp/.X11-unix 2>/dev/null | head -1 || true)"
    if [[ -n "$first" ]]; then
      export DISPLAY=":${first#X}"
    else
      export DISPLAY=":0"
    fi
  else
    export DISPLAY=":0"
  fi
fi

if [[ -z "${XAUTHORITY:-}" ]]; then
  uid="$(id -u)"
  for cand in \
    /run/user/"$uid"/.mutter-Xwaylandauth.* \
    /run/user/"$uid"/.Xauthority \
    "$HOME/.Xauthority"
  do
    # shellcheck disable=SC2086
    for f in $cand; do
      if [[ -f "$f" ]]; then
        export XAUTHORITY="$f"
        break 2
      fi
    done
  done
fi

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  exec "$ROOT/.venv/bin/python" "$ROOT/native_host/host.py"
fi
exec /usr/bin/python3 "$ROOT/native_host/host.py"
