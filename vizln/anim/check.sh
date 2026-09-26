#!/usr/bin/env bash
# Layout check for a vanim clip. No render, no video, no looking.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${VANIM_PY:-}"
for c in "$HERE/.venv/bin/python"; do
  [ -n "$PY" ] && break
  [ -x "$c" ] && PY="$c"
done
[ -n "$PY" ] || { echo "no python with manim found; set VANIM_PY" >&2; exit 1; }
if [ "${1:-}" = "--self-test" ]; then
  # prove the checker still collects. it once reported clean while collecting nothing.
  out="$("$PY" "$HERE/check.py" "$HERE/examples/faults.py" 2>&1 || true)"
  echo "$out"
  missing=0
  for kind in off-frame overlap too-small ink-over-text dot-collision; do
    echo "$out" | grep -q "$kind" || { echo "SELF-TEST FAILED: no $kind finding" >&2; missing=1; }
  done
  [ "$missing" = 0 ] && echo "self-test passed: the checker still collects"
  exit "$missing"
fi

exec "$PY" "$HERE/check.py" "$@"
