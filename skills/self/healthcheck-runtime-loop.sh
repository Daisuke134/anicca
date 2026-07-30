#!/usr/bin/env bash
# healthcheck-runtime-loop.sh — #7 H4 self-heal for the launchd-managed runtime/loop instances.
# healthcheck-lib.sh already covers the openclaw-style tmux loops (capafy/reddit/life-manager); this
# is the missing sibling for the three canonical Anicca-colony instances (spec §19/§25), which run
# `runtime/loop/index.mjs` directly under launchd (no tmux session to inspect):
#   anicca-a3cdd4 — com.anicca.daemon      (KeepAlive, body ~/.anicca)
#   Franklin      — ai.anicca.franklin-loop (KeepAlive, body ~/.blockrun) — migrated 2026-07-08 from
#                   the retired ai.anicca.franklin-sol StartInterval sol-trade job (franklin-loop-revival)
#   claude-p PM   — ai.anicca.pm-earner    (StartInterval 600s, body ~/.anicca-founder/agents/polymarket-agent)
# + ai.anicca.founder-loop (claude-p's separate low-priority "proxy body", wallet 0x810f, §25) —
#   checked too since it is still a live body sharing this infra, but is not one of the 3 canonical
#   earners.
#
# Health signal (KeepAlive vs StartInterval need DIFFERENT "dead" definitions):
#   - Job vanished from `launchctl list` entirely (unloaded/plist broken) → DEAD for either kind.
#   - KeepAlive job present but PID column is "-" → DEAD (should always have a live PID) → restart via
#     `launchctl kickstart -k`.
#   - StartInterval job's PID is "-" between runs → NORMAL, not a fault (only fires periodically).
#   - Either kind: the REAL output artifact (ledger.jsonl / trace.jsonl / a log) hasn't grown in
#     longer than that instance's own cadence allows → STALE (alive-but-stuck) → escalate to
#     self-fix.sh (same detached-Opus-fixer mechanism healthcheck-lib.sh already uses for the tmux
#     loops), never a hardcoded "this is broken" guess — the fixer reads the real logs itself.
#
# The Life Manager OUTBOUND rail (apps/life-manager, spec 2026-07-30 TODO #4) is watched here too:
#   outbound-pass   — ai.anicca.life-manager-outbound        (StartCalendarInterval, daily 07:30)
#   outbound-verify — ai.anicca.life-manager-outbound-verify (StartCalendarInterval, daily 09:00)
# It was added because the connector loop it replaces died on 2026-07-18 and ran rc=1 for 12 days
# with nobody watching: no entry here meant no scream. Both entries stat the SAME heartbeat, the one
# runtime/loop/outbound/streak.mjs::heartbeatPath() writes — see OUTBOUND_BEAT below.
#
# Usage: bash healthcheck-runtime-loop.sh          # check all
#        bash healthcheck-runtime-loop.sh <name>   # check one: franklin | founder-proxy |
#                                                  #   outbound-pass | outbound-verify
# NOT wired into cron/launchd by this script — scheduling is a separate, reviewed step (matches the
# #25 TELEM collector precedent: build + verify manually first).
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$HOME/.local/state/life-manager/logs/healthcheck-runtime-loop.log"; mkdir -p "$(dirname "$LOG")"
now=$(date +%s)

# hrl_pick_pid — PURE parser for a `launchctl list` listing on stdin (same convention as
# hrl_classify below: no I/O of its own, so a test can feed it a synthetic listing). launchctl
# prints "PID<TAB>STATUS<TAB>LABEL", so the label is matched EXACTLY on field 3.
#   Exact match is load-bearing, not tidiness: "ai.anicca.life-manager-outbound" is a strict PREFIX
#   of "ai.anicca.life-manager-outbound-verify", so the old substring grep would have let the verify
#   job's row answer for an UNLOADED pass job — the loop would read as alive while being dead, which
#   is the exact failure this file exists to catch.
# Never exits early: draining the stream avoids the SIGPIPE-under-pipefail spurious-empty-result bug
# that `grep -q` caused here (same fix as colony-status.sh).
# Prints the PID column ("-" or a number) of the first exact match, or "" if the job isn't loaded.
hrl_pick_pid() { awk -v want="$1" '$3 == want && !seen { print $1; seen = 1 }'; }
if [ "${1:-}" = "--pick-pid" ]; then hrl_pick_pid "${2:-}"; exit 0; fi

loop_pid() { launchctl list 2>/dev/null | hrl_pick_pid "$1"; }

artifact_age_min() {
  [ -f "$1" ] || { echo -1; return; }
  echo $(( (now - $(stat -f %m "$1" 2>/dev/null || echo 0)) / 60 ))
}

# hrl_classify — PURE decision predicate (no side effects, no I/O beyond its args), mirrors this
# codebase's own testing convention (healthcheck-lib.sh's hc_is_stuck_pane / self-fix.sh's
# sf_should_continue): a script sourced by a test can call this directly and assert the OUTCOME
# string without ever spawning a real kickstart/self-fix. args: <pid-or-dash-or-empty> <keepalive|
# interval> <artifact-age-min, -1 if missing> <stale-minutes-limit>. Prints exactly one of:
# DEAD_UNLOADED | DEAD_NO_PID | MISSING_ARTIFACT | STALE | OK.
hrl_classify() {
  local pid="$1" kind="$2" age="$3" stale_min="$4"
  if [ -z "$pid" ]; then echo DEAD_UNLOADED; return; fi
  if [ "$kind" = "keepalive" ] && [ "$pid" = "-" ]; then echo DEAD_NO_PID; return; fi
  if [ "$age" -lt 0 ]; then echo MISSING_ARTIFACT; return; fi
  if [ "$age" -ge "$stale_min" ]; then echo STALE; return; fi
  echo OK
}
if [ "${1:-}" = "--classify" ]; then hrl_classify "${2:-}" "${3:-}" "${4:-0}" "${5:-0}"; exit 0; fi

# ------------------------------------------------------------------ OUTBOUND rail registration
#
# OUTBOUND_BEAT is the heartbeat both outbound loops touch. It MUST stay byte-identical to
# runtime/loop/outbound/streak.mjs::heartbeatPath() — apps/life-manager/scripts/
# outbound-guardian-wiring.test.js pins the two strings against each other so a rename fails a test
# instead of silently un-watching the loop. It is deliberately NOT under the legacy .openclaw root:
# apps/life-manager/scripts/scan-legacy-paths.js fails the build on that root, and lib/runtime-paths.js
# rejects it, so <home>/.local/state/life-manager is the canonical portable data root.
OUTBOUND_BEAT="$HOME/.local/state/life-manager/.outbound-last-pass"

# Stale limits, derived from the two schedules rather than picked by feel:
#   pass fires 07:30, verify fires 09:00, and BOTH touch OUTBOUND_BEAT (streak.mjs::touchHeartbeat is
#   called by lib/outbound-runtime.js and scripts/outbound-verify.js alike). So:
#     - both loops healthy  → the oldest the file legitimately gets is 09:00 → 07:30 next day = 1350 min
#     - exactly one loop dead → the survivor still touches once a day → the age reaches 1440 min
#     - both dead            → the age grows without bound
#   1410 (23h30) therefore sits in the only window that distinguishes "healthy" from "half-dead":
#   above the 1350-min healthy maximum (60 min of launchd drift slack) and below the 1440-min mark a
#   single missed daily touch reaches. The guardian itself runs every 300s, so a 30-min detection
#   margin is ~6 evaluations wide.
OUTBOUND_PASS_STALE_MIN=1410
#   1470 (24h30) is deliberately ABOVE a full day: the verify entry is the "nothing touched this at
#   all for over a day" alarm. Staggering it 60 min behind the pass entry means one shared-heartbeat
#   outage escalates self-fix once first, not twice at the same instant.
#   Consequence stated honestly: because the artifact is shared, freshness alone cannot say WHICH of
#   the two loops is dead. The per-label DEAD_UNLOADED check below is what distinguishes them.
OUTBOUND_VERIFY_STALE_MIN=1470

# Machine-readable registration, for the wiring test (and for a human debugging a scratch HOME).
if [ "${1:-}" = "--outbound-config" ]; then
  echo "$OUTBOUND_BEAT $OUTBOUND_PASS_STALE_MIN $OUTBOUND_VERIFY_STALE_MIN"; exit 0
fi

# --classify-artifact — same pure query as --classify, but reads the REAL file's mtime first, so a
# test exercises artifact_age_min and hrl_classify together against a real heartbeat on disk.
# args: <pid-or-dash-or-empty> <keepalive|interval> <artifact-path> <stale-minutes-limit>
if [ "${1:-}" = "--classify-artifact" ]; then
  hrl_classify "${2:-}" "${3:-}" "$(artifact_age_min "${4:-}")" "${5:-0}"; exit 0
fi

_selffix() {
  echo "$(date '+%F %T') give-up -> self-fix.sh $1" >> "$LOG"
  bash "$HERE/self-fix.sh" "$1" "$2" >> "$LOG" 2>&1 || echo "$(date '+%F %T') self-fix launch failed" >> "$LOG"
}

# check — orchestrator: gathers real state, classifies (pure), then acts on the classification.
# args: <display-name> <exact-launchd-label> <keepalive|interval> <artifact-path> <stale-minutes>
check() {
  local name="$1" label="$2" kind="$3" artifact="$4" stale_min="$5"
  local pid; pid="$(loop_pid "$label")"
  local age; age=$(artifact_age_min "$artifact")
  local verdict; verdict="$(hrl_classify "$pid" "$kind" "$age" "$stale_min")"
  case "$verdict" in
    DEAD_UNLOADED)
      echo "[$name] DEAD — launchd job '$label' not found in launchctl list (unloaded or plist broken)"
      _selffix "$name" "the launchd job '$label' for the $name instance has vanished from launchctl list entirely (unloaded, or its plist is missing/broken) — diagnose why (check ~/Library/LaunchAgents/$label.plist exists and is valid, check launchctl error) and get it loaded again, verify with launchctl list."
      ;;
    DEAD_NO_PID)
      echo "[$name] DEAD — job '$label' loaded but no running PID (KeepAlive should always have one) — kickstarting"
      launchctl kickstart -k "gui/$(id -u)/$label" >> "$LOG" 2>&1 || true
      echo "$(date '+%F %T') kickstarted $label (was dead, no PID)" >> "$LOG"
      ;;
    MISSING_ARTIFACT)
      echo "[$name] job alive (pid=$pid) but artifact MISSING: $artifact — cannot judge freshness"
      ;;
    STALE)
      echo "[$name] STALE — $artifact last wrote ${age}min ago (limit ${stale_min}min), pid=$pid"
      _selffix "$name" "the $name loop is alive (launchd pid=$pid, job=$label) but its real output artifact $artifact has not been updated in ${age} minutes (limit ${stale_min}) — diagnose why it stopped producing real passes (read the actual recent log/ledger lines and any error) and fix it."
      ;;
    OK)
      echo "[$name] OK — pid=$pid, artifact ${age}min old (limit ${stale_min}min)"
      ;;
  esac
}

TARGET="${1:-all}"
echo "=== healthcheck-runtime-loop $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
# RETIRED 2026-07-12 (Dais): a3cdd4/automaton = paused until Conway Claude ships; pm-earner = retired
# (pm goes via pm-deterministic + agent-economy menu only). Watching them caused self-heal to REVIVE the
# intentionally-disabled plists (rename undone within ~1h → three false-DONE incidents). Do not re-add.
# [ "$TARGET" = all -o "$TARGET" = a3cdd4 ]       && check "anicca-a3cdd4"  "com.anicca.daemon"      keepalive "$HOME/.anicca/state/ledger.jsonl" 20
[ "$TARGET" = all -o "$TARGET" = franklin ]     && check "Franklin"       "ai.anicca.franklin-loop" keepalive "$HOME/.blockrun/state/ledger.jsonl" 20
# [ "$TARGET" = all -o "$TARGET" = pm-earner ]    && check "claude-p-pm"    "ai.anicca.pm-earner"    interval  "$HERE/../earn/polymarket-trade/earner.log" 40
[ "$TARGET" = all -o "$TARGET" = founder-proxy ] && check "claude-p-proxy" "ai.anicca.founder-loop" keepalive "$HOME/.anicca-founder/state/ledger.jsonl" 120
# OUTBOUND rail (spec 2026-07-30 §8 TODO #4). Both are StartCalendarInterval jobs, so a "-" PID
# between runs is NORMAL (kind=interval) and only DEAD_UNLOADED / STALE mean something is wrong.
[ "$TARGET" = all -o "$TARGET" = outbound-pass ]   && check "outbound-pass"   "ai.anicca.life-manager-outbound"        interval "$OUTBOUND_BEAT" "$OUTBOUND_PASS_STALE_MIN"
[ "$TARGET" = all -o "$TARGET" = outbound-verify ] && check "outbound-verify" "ai.anicca.life-manager-outbound-verify" interval "$OUTBOUND_BEAT" "$OUTBOUND_VERIFY_STALE_MIN"
exit 0
