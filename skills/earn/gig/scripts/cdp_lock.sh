#!/usr/bin/env bash
# cdp_lock.sh — shared advisory lock so the gig CORE (:27 pass) and the reality-VERIFIER
# (:45 auditor spawn) never drive the :9222 daily-driver tab at the SAME time (gig L1-d).
#
# Both attach to the same coconala page tab via get_tab(); if a long core pass (>18min)
# overlaps the verifier at :45, one Page.navigate yanks the page out from under the other,
# corrupting an in-progress 応募/フォーム入力 or producing a false verdict. This lock makes
# them mutually exclusive WITHOUT opening/closing/duplicating the daily-driver tab (which the
# daily-driver-tab rule forbids): whoever holds the lock drives; the other waits or defers.
#
# Usage (source this file, then call the functions):
#   source ~/profitable-claude/skills/gig-work/scripts/cdp_lock.sh
#   if cdp_lock_acquire "core" 120; then  # owner label, max wait secs
#       ...drive :9222...
#       cdp_lock_release
#   else
#       echo "deferred: :9222 busy"       # could not acquire within timeout
#   fi
#
# Crash-safety: the lock is a mkdir dir with a meta file holding owner+epoch. If the holder
# died without releasing, the lock is auto-STOLEN once it is older than CDP_LOCK_STALE_SECS
# (default 1500s = 25min, longer than any real browser phase) so a crashed holder never
# blocks the loop forever.
CDP_LOCK_DIR="${CDP_LOCK_DIR:-$HOME/gig/.cdp-9222.lock}"
CDP_LOCK_STALE_SECS="${CDP_LOCK_STALE_SECS:-1500}"

_cdp_lock_mtime() {
  # A holder killed between mkdir and metadata write still leaves a reclaimable
  # lock.  Fall back to the directory mtime so crash recovery is bounded.
  stat -f %m "$CDP_LOCK_DIR/meta" 2>/dev/null \
    || stat -c %Y "$CDP_LOCK_DIR/meta" 2>/dev/null \
    || stat -f %m "$CDP_LOCK_DIR" 2>/dev/null \
    || stat -c %Y "$CDP_LOCK_DIR" 2>/dev/null \
    || echo 0
}

cdp_lock_acquire() {
  local owner="${1:-unknown}" timeout="${2:-120}" waited=0
  mkdir -p "$(dirname "$CDP_LOCK_DIR")" 2>/dev/null || true
  while :; do
    if mkdir "$CDP_LOCK_DIR" 2>/dev/null; then
      printf '%s %s\n' "$owner" "$(date +%s)" > "$CDP_LOCK_DIR/meta" 2>/dev/null || true
      return 0
    fi
    # held by someone else — steal if stale (holder likely crashed)
    local held now age
    held="$(_cdp_lock_mtime)"; now="$(date +%s)"
    age=$(( now - held ))
    if [ "$held" -gt 0 ] && [ "$age" -ge "$CDP_LOCK_STALE_SECS" ]; then
      rm -rf "$CDP_LOCK_DIR" 2>/dev/null || true
      continue
    fi
    if [ "$waited" -ge "$timeout" ]; then
      return 1
    fi
    sleep 5
    waited=$(( waited + 5 ))
  done
}

cdp_lock_release() {
  rm -rf "$CDP_LOCK_DIR" 2>/dev/null || true
}
