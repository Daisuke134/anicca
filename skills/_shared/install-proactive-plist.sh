#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
# install-proactive-plist.sh — sprint-3 #30
# Per-slot launchd plist installer. Idempotent. Darwin-only.
# Single source of PURE logic in lib/plist_render.py (FIND-007 fix).
#
# Usage: install-proactive-plist.sh <slot>
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY=python3
# Tests can override the launchctl binary to simulate failures (EDGE-E5).
# Production foot-gun guard (FIND-2-001): the override is REJECTED unless the
# binary lives under a recognized temp root (= $TMPDIR | /tmp | /private/tmp |
# /private/var/folders). A production cron that accidentally exports
# LAUNCHCTL_BIN to anything else dies loud instead of silently executing an
# attacker binary with launchctl's argv. Logged to stderr when active.
LAUNCHCTL="launchctl"
if [[ -n "${LAUNCHCTL_BIN:-}" ]]; then
  _RESOLVED="$(cd "$(dirname "$LAUNCHCTL_BIN")" 2>/dev/null && pwd -P)/$(basename "$LAUNCHCTL_BIN")"
  _ALLOWED_PREFIXES=("${TMPDIR%/}" "/tmp" "/private/tmp" "/private/var/folders" "/var/folders")
  _OK=0
  for _PFX in "${_ALLOWED_PREFIXES[@]}"; do
    [[ -n "$_PFX" && "$_RESOLVED" == "$_PFX"/* ]] && _OK=1 && break
  done
  if [[ "$_OK" != "1" ]]; then
    echo "LAUNCHCTL_BIN must resolve under a temp root; got: $_RESOLVED" >&2
    exit 9
  fi
  if [[ ! -x "$_RESOLVED" ]]; then
    echo "LAUNCHCTL_BIN not executable: $_RESOLVED" >&2
    exit 9
  fi
  echo "WARN: LAUNCHCTL_BIN override active (test mode): $_RESOLVED" >&2
  LAUNCHCTL="$_RESOLVED"
fi

# FIND-005 fix: per-invocation private tmpfile, no shared /tmp paths (TOCTOU).
TMPROOT="${TMPDIR:-/tmp}"
TMPERR="$(mktemp "$TMPROOT/iplv.XXXXXXXX")"
trap 'rm -f "$TMPERR"' EXIT

# ─── REQ-A4 ordering: validate FIRST, before any FS/launchctl side-effect ────
# (Calling the PURE validator via subprocess is permitted because it has no
#  filesystem or launchctl side-effect of its own; spec REQ-A4 forbids
#  side-effecting subprocesses, not the read-only validator call. The validator
#  is also re-asserted inside render_plist (defense in depth).)
SLOT="${1:-}"
if [[ -z "$SLOT" ]]; then
  echo "Usage: install-proactive-plist.sh <slot>" >&2
  exit 2
fi
if ! ( cd "$SHARED_DIR" && "$PY" -m lib.plist_render validate "$SLOT" 2>"$TMPERR" ); then
  echo "invalid slot: validation failed — $(cat "$TMPERR" 2>/dev/null)" >&2
  exit 3
fi

# ─── EDGE-E6 Darwin-only guard ──────────────────────────────────────
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Darwin only" >&2
  exit 2
fi

# ─── REQ-A2 pin: must be installing from $LIFE_MANAGER_REPO ───────
CANONICAL_HOME="$LIFE_MANAGER_REPO"
REPO_ROOT="$(cd "$SHARED_DIR/.." && cd .. && pwd)"
if [[ "$REPO_ROOT" != "$CANONICAL_HOME" ]]; then
  echo "anicca repo root mismatch: expected $CANONICAL_HOME, got $REPO_ROOT" >&2
  exit 4
fi

UID_NUM="$(id -u)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/.local/state/life-manager/logs"
LABEL="ai.anicca.${SLOT}-proactive"
PLIST="$LAUNCH_AGENTS/$LABEL.plist"

# EDGE-E1 / E2: ensure dirs exist
mkdir -p "$LAUNCH_AGENTS" "$LOG_DIR"

# ─── Render canonical plist content (PURE call) ─────────────────────
NEW_CONTENT="$( cd "$SHARED_DIR" && "$PY" -m lib.plist_render render "$SLOT" "$CANONICAL_HOME" "$LOG_DIR" "$PLIST" )" \
  || { echo "render failed" >&2; exit 5; }

# ─── REQ-E2: detect cross-path collision and bootout if needed ──────
PRINT_OUT="$("$LAUNCHCTL" print "gui/$UID_NUM/$LABEL" 2>/dev/null || true)"
BOOTED_OUT_STALE=0
if [[ -n "$PRINT_OUT" ]]; then
  EXISTING_PATH="$( cd "$SHARED_DIR" && printf '%s' "$PRINT_OUT" | "$PY" -m lib.plist_render parse-path 2>/dev/null || true )"
  if [[ -n "$EXISTING_PATH" && "$EXISTING_PATH" != "$PLIST" ]]; then
    "$LAUNCHCTL" bootout "gui/$UID_NUM/$LABEL" >/dev/null 2>&1 || true
    # FIND-001 fix: track that we removed a stale loaded job so the idempotent
    # branch below knows it MUST re-bootstrap, even if the canonical disk
    # plist already exists byte-identical (= the bootout left zero loaded jobs).
    BOOTED_OUT_STALE=1
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

# FIND-001 fix: even if disk is byte-identical, if we just booted-out a stale
# job we MUST bootstrap to leave one loaded job at the canonical path.
NEEDS_BOOTSTRAP=$NEEDS_WRITE
if [[ "$BOOTED_OUT_STALE" == "1" ]]; then
  NEEDS_BOOTSTRAP=1
fi

if [[ "$NEEDS_WRITE" == "1" ]]; then
  # REQ-B2: rewrite + bootout/bootstrap to pick up the new template
  if [[ -f "$PLIST" ]]; then
    "$LAUNCHCTL" bootout "gui/$UID_NUM/$LABEL" >/dev/null 2>&1 || true
  fi
  printf '%s' "$NEW_CONTENT" > "$PLIST"
fi

if [[ "$NEEDS_BOOTSTRAP" == "1" ]]; then
  TMPBERR="$(mktemp "$TMPROOT/iplb.XXXXXXXX")"
  trap 'rm -f "$TMPERR" "$TMPBERR"' EXIT
  if ! "$LAUNCHCTL" bootstrap "gui/$UID_NUM" "$PLIST" 2>"$TMPBERR"; then
    # EDGE-E5: bootstrap failure → rollback (remove the disk plist so we
    # don't leave a half-loaded job).
    BOOT_ERR="$(cat "$TMPBERR" 2>/dev/null)"
    rm -f "$PLIST"
    echo "launchctl bootstrap failed: $BOOT_ERR" >&2
    exit 6
  fi
fi

# ─── REQ-C1: confirm loaded post-install ────────────────────────────
if ! "$LAUNCHCTL" print "gui/$UID_NUM/$LABEL" >/dev/null 2>&1; then
  echo "post-install launchctl print failed for $LABEL" >&2
  exit 7
fi

# ─── REQ-C2 / NFR-3: one-line summary on stdout ─────────────────────
echo "installed $LABEL (plist=$PLIST, interval=300s)"
