#!/usr/bin/env bash
# install-proactive-plist.sh — sprint-3 #30
# Per-slot launchd plist installer. Idempotent. Darwin-only.
# Single source of PURE logic in lib/plist_render.py (FIND-007 fix).
#
# Usage: install-proactive-plist.sh <slot>
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY=python3

# ─── REQ-A4 ordering: validate FIRST, before any side-effect ────────
SLOT="${1:-}"
if [[ -z "$SLOT" ]]; then
  echo "Usage: install-proactive-plist.sh <slot>" >&2
  exit 2
fi
# Run validate from SHARED_DIR so lib.plist_render resolves
if ! ( cd "$SHARED_DIR" && "$PY" -m lib.plist_render validate "$SLOT" 2>/tmp/.iplv.err ); then
  echo "invalid slot: validation failed — $(cat /tmp/.iplv.err 2>/dev/null)" >&2
  rm -f /tmp/.iplv.err
  exit 3
fi
rm -f /tmp/.iplv.err

# ─── EDGE-E6 Darwin-only guard ──────────────────────────────────────
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Darwin only" >&2
  exit 2
fi

# ─── REQ-A2 pin: must be installing from /Users/operator/anicca ───────
CANONICAL_HOME="/Users/operator/anicca"
REPO_ROOT="$(cd "$SHARED_DIR/.." && cd .. && pwd)"
if [[ "$REPO_ROOT" != "$CANONICAL_HOME" ]]; then
  echo "anicca repo root mismatch: expected $CANONICAL_HOME, got $REPO_ROOT" >&2
  exit 4
fi

UID_NUM="$(id -u)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/.openclaw/logs"
LABEL="ai.anicca.${SLOT}-proactive"
PLIST="$LAUNCH_AGENTS/$LABEL.plist"

# EDGE-E1 / E2: ensure dirs exist
mkdir -p "$LAUNCH_AGENTS" "$LOG_DIR"

# ─── Render canonical plist content (PURE call) ─────────────────────
NEW_CONTENT="$( cd "$SHARED_DIR" && "$PY" -m lib.plist_render render "$SLOT" "$CANONICAL_HOME" "$LOG_DIR" "$PLIST" )" \
  || { echo "render failed" >&2; exit 5; }

# ─── REQ-E2: detect cross-path collision and bootout if needed ──────
PRINT_OUT="$(launchctl print "gui/$UID_NUM/$LABEL" 2>/dev/null || true)"
if [[ -n "$PRINT_OUT" ]]; then
  EXISTING_PATH="$( cd "$SHARED_DIR" && printf '%s' "$PRINT_OUT" | "$PY" -m lib.plist_render parse-path 2>/dev/null || true )"
  if [[ -n "$EXISTING_PATH" && "$EXISTING_PATH" != "$PLIST" ]]; then
    launchctl bootout "gui/$UID_NUM/$LABEL" >/dev/null 2>&1 || true
  fi
fi

# ─── REQ-B1 idempotent: same content on disk = no rewrite ───────────
NEEDS_WRITE=1
if [[ -f "$PLIST" ]]; then
  EXIST_DIGEST="$( cd "$SHARED_DIR" && cat "$PLIST" | "$PY" -m lib.plist_render digest 2>/dev/null || echo "")"
  NEW_DIGEST="$( cd "$SHARED_DIR" && printf '%s' "$NEW_CONTENT" | "$PY" -m lib.plist_render digest 2>/dev/null || echo "")"
  if [[ -n "$EXIST_DIGEST" && "$EXIST_DIGEST" == "$NEW_DIGEST" ]]; then
    NEEDS_WRITE=0
  fi
fi

if [[ "$NEEDS_WRITE" == "1" ]]; then
  # REQ-B2: rewrite + bootout/bootstrap to pick up the new template
  if [[ -f "$PLIST" ]]; then
    launchctl bootout "gui/$UID_NUM/$LABEL" >/dev/null 2>&1 || true
  fi
  printf '%s' "$NEW_CONTENT" > "$PLIST"
  if ! launchctl bootstrap "gui/$UID_NUM" "$PLIST" 2>/tmp/.iplb.err; then
    # EDGE-E5: bootstrap failure → rollback (remove the disk plist so we
    # don't leave a half-loaded job).
    BOOT_ERR="$(cat /tmp/.iplb.err 2>/dev/null)"
    rm -f "$PLIST" /tmp/.iplb.err
    echo "launchctl bootstrap failed: $BOOT_ERR" >&2
    exit 6
  fi
  rm -f /tmp/.iplb.err
fi

# ─── REQ-C1: confirm loaded post-install ────────────────────────────
if ! launchctl print "gui/$UID_NUM/$LABEL" >/dev/null 2>&1; then
  echo "post-install launchctl print failed for $LABEL" >&2
  exit 7
fi

# ─── REQ-C2 / NFR-3: one-line summary on stdout ─────────────────────
echo "installed $LABEL (plist=$PLIST, interval=300s)"
