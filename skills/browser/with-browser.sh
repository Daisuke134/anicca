#!/usr/bin/env bash
# Hold one registered browser identity for exactly one command lifetime.
set -uo pipefail

IDENTITY="${1:-}"
shift || true
[ "${1:-}" = "--" ] && shift

if [ -z "$IDENTITY" ] || [ "$#" -eq 0 ]; then
  echo "usage: with-browser.sh IDENTITY -- command..." >&2
  exit 64
fi

GUARD="${AI_BROWSER_GUARD:-$HOME/.config/ai/bin/browser-guard.sh}"
WAIT_SECONDS="${BROWSER_WAIT_SECONDS:-300}"
CDP=""
deadline=$(( $(date +%s) + WAIT_SECONDS ))

while :; do
  # Command substitution runs acquire in a short-lived shell. Bind the lease to this wrapper,
  # which remains alive until the browser command and its official readback have both exited.
  CDP="$(AI_BROWSER_HOLDER_PID=$$ "$GUARD" acquire "$IDENTITY" 2>/dev/null)" && break
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "with-browser: $IDENTITY busy for ${WAIT_SECONDS}s" >&2
    exit 75
  fi
  sleep 10
done

released=0
child=0
release_once() {
  [ "$released" -eq 1 ] && return
  released=1
  [ "$child" -ne 0 ] && kill -TERM "$child" 2>/dev/null || true
  "$GUARD" release "$IDENTITY" >/dev/null 2>&1 || true
}
trap release_once EXIT INT TERM HUP

CDP="$CDP" "$@" &
child=$!
wait "$child"
status=$?
release_once
exit "$status"
