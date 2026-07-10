#!/usr/bin/env bash
# healthcheck-lib.sh — ONE shared supervisor used by every loop's healthcheck (FIND-011). Detects, in order:
# (a) DEAD session, (b) STUCK-asking-a-human interactive prompt (FIND-001), (c) STALE liveness heartbeat, (d)
# running-but-producing-NOTHING output staleness (FIND-009). Recovers by restart w/ backoff; on give-up it calls
# self-fix.sh DIRECTLY to spawn an Opus fixer (FIND-006).
# AUTHORITATIVE success signal = the REAL output artifact (published.jsonl / posts.jsonl freshness, cross-checked
# live by verify-loops.sh) — NOT any self-graded marker (FIND-015): a fixer that lies "SUCCESS" but leaves the
# output stale is re-escalated here anyway, because (d) reads the artifact, never the marker.
# Caller sets: HC_LOOP HC_SOCK HC_SESSION HC_HB HC_START HC_STALE_MIN HC_CLI HC_OUTPUT HC_OUTPUT_STALE_HRS HC_SELFFIX_HINT
#
# ★ REQ-LV-104 scope note ★ — this shared hc_run() (incl. its OUT_STALE_HRS artifact-age check in
# step (d)) is sourced ONLY by capafy-loop-healthcheck.sh / reddit-loop-healthcheck.sh /
# life-manager-loop-healthcheck.sh (verified via grep, 2026-07-08). The 7 Cadence Contract loops
# (clip/affiliate/video/gig/bounty/pm-earner/founder-loop) each run their OWN standalone
# *-healthcheck.sh (e.g. video-healthcheck.sh) that does NOT call this file — their "is today's
# contract met" judgment lives in cadence.py/cadence-evidence.py via verify-loops(-audit).sh
# instead. This is intentional, not an integration gap: REQ-LV-104 explicitly keeps the old
# fresh()/stale_hrs()-style artifact-age judgment for capafy/reddit/life-manager only.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail

# FIND-014/021: single source of truth for "is this pane an idle prompt awaiting a human?" — fires ONLY on
# unambiguous input-await markers AND ONLY when NOT actively generating ("esc to interrupt" = live generation).
# test-healthcheck-lib.sh sources THIS function (no duplication → no drift).
hc_is_stuck_pane() {
  local pane="$1"
  printf '%s' "$pane" | grep -qE 'Enter to select|↑/↓ to navigate|Type something\.|Do you want to proceed' \
    && ! printf '%s' "$pane" | grep -qE 'esc to interrupt'
}

# FIND-033 (life-manager-loop 3-day outage, 2026-07-10): a near-full data volume stops macOS growing its
# swapfile, which surfaces as intermittent fork() failures ("Resource temporarily unavailable") for EVERY
# new process on the box — including this script's own tmux/pkill calls (seen directly in launchd's error
# log) and every fresh `claude` spawn. A loop that is already DEAD needs a FRESH spawn every cycle, so it
# eats this failure on every single restart while already-idle sessions (needing no new fork) sail through
# — the loop can starve indefinitely even though its own code is fine. Reclaim only caches that are 100%
# regenerable package-manager/updater caches (never model weights like whisper/ollama/HF, never
# claudevm/colima — those need Dais approval per disk-hygiene policy) so a respawn actually has room to
# start. Cheap (~1s) when disk is fine; only doing real work under the low-disk condition.
hc_reclaim_disk_if_low() {
  local free_gb; free_gb="$(df -g /System/Volumes/Data 2>/dev/null | awk 'NR==2{print $4}')"
  [ -z "${free_gb:-}" ] && free_gb="$(df -g / 2>/dev/null | awk 'NR==2{print $4}')"
  [ -z "${free_gb:-}" ] && return 0
  [ "$free_gb" -ge 3 ] 2>/dev/null && return 0
  echo "$(date '+%F %T') disk low (${free_gb}GB free) → reclaiming safe regenerable caches before respawn" >> "${LOG:-/dev/null}"
  command -v npm >/dev/null 2>&1 && npm cache clean --force >/dev/null 2>&1
  rm -rf "$HOME/.cache/uv" 2>/dev/null
  rm -rf "$HOME/Library/Caches/com.anthropic.claudefordesktop.ShipIt"/* 2>/dev/null
  rm -rf "$HOME/Library/Caches/camoufox"/* 2>/dev/null
  rm -rf "$HOME/Library/Caches/node-gyp"/* 2>/dev/null
  rm -rf "$HOME/Library/Caches/pip"/* 2>/dev/null
  command -v brew >/dev/null 2>&1 && brew cleanup -s >/dev/null 2>&1
  return 0
}

# FIND-020/026/031: acquire a per-loop lock. mkdir is atomic (one winner). A FRESH lock (<10min) = a live run → refuse
# (return 1). A STALE lock (>=10min, = a hard-killed prior run) is stolen with rm -rf (works even though the lock dir
# is NON-EMPTY due to the owner file — plain rmdir would fail and permanently disable self-heal). After (re)creating,
# claim by PID and re-verify to close the concurrent-steal race: exactly one survivor returns 0.
hc_acquire_lock() {
  local LOCK_DIR="$1" now="$2"
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    local lage=$(( ( now - $(stat -f %m "$LOCK_DIR" 2>/dev/null||echo "$now") ) / 60 ))
    if [ "$lage" -ge 10 ]; then rm -rf "$LOCK_DIR" 2>/dev/null||true; mkdir "$LOCK_DIR" 2>/dev/null || return 1
    else return 1; fi
  fi
  echo "$$" > "$LOCK_DIR/owner" 2>/dev/null; sleep 0.2
  [ "$(cat "$LOCK_DIR/owner" 2>/dev/null)" = "$$" ] || return 1
  return 0
}

hc_run() {
  local LOOP="$HC_LOOP" SOCK="$HC_SOCK" SESSION="$HC_SESSION" HB="$HC_HB" START="$HC_START"
  local STALE_MIN="$HC_STALE_MIN" CLI="$HC_CLI" OUTPUT="${HC_OUTPUT:-}" OUT_STALE_HRS="${HC_OUTPUT_STALE_HRS:-30}"
  local SELFFIX_HINT="${HC_SELFFIX_HINT:-loop produces no real output}"
  local STATE="$HOME/.openclaw/state"; mkdir -p "$STATE"
  local LOG="$HOME/.openclaw/logs/$LOOP-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
  local RESTART_LOG="$STATE/.$LOOP-restart-log"
  local now; now=$(date +%s)

  # FIND-013: lock with a staleness escape hatch. A healthcheck killed abnormally must not disable self-heal forever
  # — if the lock is older than 10min it is stale (each run finishes in seconds), so steal it.
  local LOCK_DIR="/tmp/.$LOOP-healthcheck.lock"
  hc_acquire_lock "$LOCK_DIR" "$now" || return 0
  trap 'rm -rf "$LOCK_DIR" 2>/dev/null' RETURN

  _selffix() {  # FIND-006: give-up → actually spawn the Opus fixer, not a dead note
    echo "$(date '+%F %T') give-up → self-fix.sh $LOOP" >> "$LOG"
    bash "$HOME/anicca/skills/self/self-fix.sh" "$LOOP" "$1" >> "$LOG" 2>&1 || echo "$(date '+%F %T') self-fix launch failed" >> "$LOG"
  }
  _restart() {  # backoff: >=5 restarts/60min → escalate to self-fix instead of thrashing
    local reason="$1" count=0 ts
    if [ -f "$RESTART_LOG" ]; then while IFS= read -r ts; do [ -n "$ts" ] && [ $(( now - ts )) -le 3600 ] && count=$(( count+1 )); done < "$RESTART_LOG"; fi
    if [ "$count" -ge 5 ]; then _selffix "the $LOOP loop keeps dying/stalling ($count restarts/60min; last reason: $reason). Diagnose why its cli.sh/STARTUP won't run a healthy pass and fix it."; return; fi
    echo "$now" >> "$RESTART_LOG"; pkill -f "claude --name $SESSION" 2>/dev/null||true; pkill -f "tmux -S $SOCK new-session" 2>/dev/null||true; sleep 1
    hc_reclaim_disk_if_low
    echo "$(date '+%F %T') $reason → restart" >> "$LOG"; bash "$CLI" --restart >> "$LOG" 2>&1||true
  }

  # (a) DEAD
  if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then _restart "$LOOP DEAD"; return; fi

  # (b) STUCK asking a human (FIND-001/014): fire ONLY on unambiguous input-await markers of Claude Code's interactive
  # picker/confirm/free-text, AND ONLY when the session is NOT actively generating. Active generation always shows
  # "esc to interrupt"; an idle-await prompt never does. This prevents false-restarting healthy long-running work.
  local pane; pane="$(tmux -S "$SOCK" capture-pane -t "$SESSION" -p 2>/dev/null | tail -25)"
  if hc_is_stuck_pane "$pane"; then
    echo "$(date '+%F %T') STUCK: idle interactive prompt (awaiting human input) → restart" >> "$LOG"; _restart "STUCK asking human"; return
  fi

  # (c) liveness heartbeat stale
  local hb_age m
  if [ ! -f "$HB" ]; then m="$(stat -f %m "$START" 2>/dev/null||echo "$now")"; hb_age=$(( (now-m)/60 ))
    if [ "$hb_age" -ge "$STALE_MIN" ]; then _restart "no pass in ${hb_age}min"; return; fi
  else hb_age=$(( (now-$(stat -f %m "$HB" 2>/dev/null||echo "$now"))/60 ))
    if [ "$hb_age" -ge "$STALE_MIN" ]; then _restart "STALE ${hb_age}min"; return; fi
  fi

  # (d) running but producing NOTHING real (FIND-009): the real output artifact is the ONLY success signal. If it has
  # not changed in OUT_STALE_HRS the loop is alive-but-useless (or a self-fix lied) → escalate a self-fix, once per window.
  if [ -n "$OUTPUT" ]; then
    local o_age=99999
    [ -f "$OUTPUT" ] && o_age=$(( (now-$(stat -f %m "$OUTPUT" 2>/dev/null||echo 0))/3600 ))
    if [ "$o_age" -ge "$OUT_STALE_HRS" ]; then
      local MK="$STATE/.$LOOP-output-stale-escalated"
      if [ ! -f "$MK" ] || [ "$(( (now-$(stat -f %m "$MK" 2>/dev/null||echo 0))/3600 ))" -ge "$OUT_STALE_HRS" ]; then
        touch "$MK"; _selffix "$SELFFIX_HINT (no real output for ${o_age}h; the loop is alive but STEP2/STEP3 produce nothing — find why and fix it so a real side-effect happens)."
        echo "$(date '+%F %T') ALIVE but output stale ${o_age}h → self-fix escalated" >> "$LOG"; return
      fi
    fi
    echo "$(date '+%F %T') ALIVE+fresh (hb ${hb_age}min, output ${o_age}h)" >> "$LOG"; return
  fi
  echo "$(date '+%F %T') ALIVE+fresh (hb ${hb_age}min)" >> "$LOG"
}
