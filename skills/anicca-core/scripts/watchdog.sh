#!/usr/bin/env bash
# watchdog.sh — the OUTERMOST shell: restarts Anicca's own machinery when it HANGS
# (launchd KeepAlive only catches process EXIT, not a hung-but-alive process).
# Runs every 5 min via launchd ai.anicca.watchdog. Port of the pfangueiro
# self-healing watchdog idea, adapted to Anicca.
#
# Checks (each with consensus = act only on consecutive failures, no false-positive restart):
#   1. gateway responsive  — `openclaw cron list` (talks to gateway). ~6s normal w/ 208 jobs,
#      so 35s timeout + restart only after 2 consecutive misses.
#   2. heartbeat stuck     — core-status.json status=running with ts > 25min old = stuck beat.
#   3. peer-api dead       — ops/.alive > 45min stale AND no agent-api process → reload launchd.
# Reports any ACTION to #metrics. Read-only when everything is healthy.
#
# TIER 0 of the self-heal spec (2026-07-01-openclaw-self-heal-design.md §3): THIS script IS
# the "watcher outside what it watches" (P1) — launchd, not an OpenClaw cron, so it keeps
# probing even when config invalid (F1) or the scheduler is dead (F4) kills every in-band
# health cron. Every probe/remediation is written to state/self-heal-ledger.jsonl (spec §3.3
# schema: ts/failure_class/probe_output/action_taken/verify_result/tier/escalated) — the
# audit trail proving self-heal actually happened, not a chat claim. Escalation to Telegram
# is cooldown-gated per failure_class (state/self-heal-mode.json ESCALATION_COOLDOWN_S,
# default 24h) so a flapping condition alerts once, not every 5min. Rollout mode
# (state/self-heal-mode.json {"mode":"L1"|"L2"}) gates whether F1/F4 remediation actually
# mutates anything: L1 = detect+ledger+escalate only, L2 = auto-remediate (current default —
# see the SELF_HEAL_MODE comment below for why L2 and not L1).
set -uo pipefail
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
source "$ANICCA_HOME/.env" 2>/dev/null || true
ST="$ANICCA_HOME/state"; mkdir -p "$ST"
GW_FAILS="$ST/watchdog-gw-fails"
NOW=$(date +%s)

# CONCURRENCY LOCK — a manual run + the launchd run (every 300s) once raced on the SAME
# config tmp file and left openclaw.json momentarily CORRUPT. mkdir is an atomic mutex
# (macOS ships no flock). Only one watchdog runs at a time; a run that overlaps the next
# launchd fire simply exits. A stale lock (its pid is dead) is reclaimed.
LOCK="$ST/watchdog.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -f "$LOCK/pid" ] && kill -0 "$(cat "$LOCK/pid" 2>/dev/null)" 2>/dev/null; then
    echo "watchdog: another instance running (pid $(cat "$LOCK/pid")) — skipping this run"; exit 0
  fi
  rm -rf "$LOCK"; mkdir "$LOCK" 2>/dev/null || { echo "watchdog: cannot acquire lock — skipping"; exit 0; }
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT

# TIER=0: this script IS Tier 0 — launchd, outside OpenClaw's own scheduler, per P1.
# Shared ledger/cooldown/mode-switch/telegram plumbing lives in ONE place (HARD RULE 0.17
# SSOT) since TIER 1 (tier1-remediate.sh) needs the exact same primitives — extracted
# 2026-07-04 rather than hand-copied a second time.
TIER=0
. "$ANICCA_HOME/skills/_shared/scripts/self-heal-lib.sh"
# ★ SELF_HEAL_MODE default = L2 is NOT a default invented for this refactor: F1
#   (config-repair) and F4 (gateway/scheduler restart) remediation in this script were
#   ALREADY LIVE in production before the 2026-07-04 hardening task (git
#   8e21361d..156bcf10, 2026-06-07..2026-07-01) and already passed a real fault-injection
#   E2E (state/events/events-2026-07-01.jsonl: watchdog.config_repair
#   removed=bogusext/bogusext2/hivemind, all successful, zero false-remediations recorded
#   since). Forcing it back to L1 would be a live regression — silently reintroducing the
#   exact human-in-the-loop gap (Dais manually noticing F1/F4) this system exists to remove.

# P2 VERIFY-AFTER-REMEDIATION — spec §3.1 P2: "restart でなく root-cause fix。修復後は必ず
# probe 再実行で green 検証". A restart isn't "done" until the gateway actually answers again.
# Retries a few times (openclaw gateway restart is async — the new process takes a few
# seconds to bind) before giving up and reporting unconfirmed (never asserts green it hasn't
# measured — adversary finding: previously this asserted "restarted" without re-probing).
wait_for_gateway_ready() {
  local tries=0
  while [ "$tries" -lt 6 ]; do
    sleep 5
    if timeout 20 openclaw cron list >/dev/null 2>&1; then
      echo "restarted_verified"
      return 0
    fi
    tries=$(( tries + 1 ))
  done
  echo "restarted_unconfirmed"
  return 1
}

# 0) CONFIG VALIDITY — the ROOT of the 2026-07-01 outage. EVERY check below calls
#    `openclaw ...`, which REFUSES to run when config is invalid, so the whole watchdog
#    (INCLUDING its own `openclaw gateway restart`) silently becomes a no-op and the
#    gateway stays hung "for long". So this MUST run first and repair config using NO
#    openclaw dependency (pure python) — mirrors the manual hivemind fix that unbricked it.
CFG="$ANICCA_HOME/openclaw.json"
VALIDATE_OUT=$(timeout 25 openclaw config validate 2>&1) || true
if [ -z "$VALIDATE_OUT" ]; then
  # 2026-07-04 real incident caught by this test suite: `timeout 25 openclaw config validate`
  # returning EMPTY (killed by timeout mid-write, or gateway mid-restart producing no stdout
  # yet) was previously treated as "invalid, no recognized cause" and escalated on EVERY such
  # blip (see state/events/events-2026-07-04.jsonl ts=1783105287, detail=""). That's a
  # transient probe failure, not a config fact — skip this cycle's config check rather than
  # cry wolf; the next run 5min later will see the real state.
  ledger "F1_config_invalid" "$VALIDATE_OUT" "skipped (empty/timeout probe output, not a config fact)" "unknown" "false"
  ev watchdog.config_probe_empty detail="timeout_or_empty"
elif ! echo "$VALIDATE_OUT" | grep -q "Config valid"; then
  # offending plugin entries appear as "plugins.entries.<name>: ..." in validate output.
  # Only trust a name if its extension dir is ACTUALLY broken (missing dist entrypoint) —
  # otherwise a valid plugin mentioned in a warning could be deleted for no reason
  # (adversary finding #3: false-positive deletion).
  CANDIDATES=$(echo "$VALIDATE_OUT" | grep -oE "plugins\.entries\.[a-zA-Z0-9_-]+" | sed 's/.*\.//' | sort -u)
  BAD=""
  for p in $CANDIDATES; do
    if [ -d "$ANICCA_HOME/extensions/$p" ] && [ ! -f "$ANICCA_HOME/extensions/$p/dist/index.js" ]; then
      BAD="$BAD $p"
    fi
  done
  BAD=$(echo "$BAD" | xargs -n1 2>/dev/null | sort -u)
  if [ "$SELF_HEAL_MODE" = "L1" ]; then
    # report-only: detect + ledger + escalate, do NOT touch openclaw.json
    record_action "F1_config_invalid" "🔎 [L1 report-only] config INVALID (offending:${BAD:-none}) — NOT auto-repaired (mode=L1)" \
      "$VALIDATE_OUT" "none (L1 report-only mode)" "still_invalid"
    ev watchdog.config_invalid_report_only offending="$(echo $BAD | tr '\n' ',')"
  elif [ -n "$BAD" ] && [ -f "$CFG" ]; then
    BAK="$CFG.watchdog-bak-$(date +%s)"
    cp "$CFG" "$BAK"
    for p in $BAD; do
      # atomic write (tmp+rename, adversary finding #2): a crash mid-write leaves the
      # ORIGINAL file intact, never a truncated/corrupt config.
      python3 - "$CFG" "$p" <<'PY' 2>/dev/null || true
import json,sys,os
cfg,p=sys.argv[1],sys.argv[2]
d=json.load(open(cfg))
d.get("plugins",{}).get("entries",{}).pop(p,None)
tmp=cfg+".watchdog-tmp."+str(os.getpid())  # per-PID tmp: concurrent writers never share it
json.dump(d,open(tmp,"w"),indent=2,ensure_ascii=False)
os.replace(tmp,cfg)
PY
      mkdir -p "$ANICCA_HOME/.disabled-extensions"
      mv "$ANICCA_HOME/extensions/$p" "$ANICCA_HOME/.disabled-extensions/$p-$(date +%s)" 2>/dev/null || true
    done
    if timeout 25 openclaw config validate 2>&1 | grep -q "Config valid"; then
      openclaw gateway restart >/dev/null 2>&1 || true
      GWVERIFY=$(wait_for_gateway_ready)
      record_action "F1_config_invalid" "🩹 config was INVALID (offending: $(echo $BAD | tr '\n' ' ')) → removed + gateway restart ($GWVERIFY)" \
        "$VALIDATE_OUT" "removed plugins.entries.[$(echo $BAD | tr '\n' ',')] + gateway restart" "config_valid+$GWVERIFY"
      ev watchdog.config_repair removed="$(echo $BAD | tr '\n' ',')"
    else
      # repair attempt made it no better (or worse) — restore original config so we never
      # leave the file in a worse state than we found it (adversary finding #2).
      cp "$BAK" "$CFG"
      record_action "F1_config_invalid" "🚨 config INVALID, auto-repair did not fix it — restored original, MANUAL FIX NEEDED: $VALIDATE_OUT" \
        "$VALIDATE_OUT" "attempted removal of [$(echo $BAD | tr '\n' ',')], failed, restored original" "still_invalid"
      ev watchdog.config_repair_failed offending="$(echo $BAD | tr '\n' ',')"
    fi
  else
    # adversary finding #1 (CRITICAL): invalid config but no recognized/fixable offender
    # (JSON syntax error, non-plugin cause, etc). Previously this fell through SILENTLY
    # forever — the exact class of outage this check exists to kill. Escalate (cooldown-gated).
    record_action "F1_config_invalid" "🚨 config INVALID, no auto-fixable cause found — MANUAL FIX NEEDED: $VALIDATE_OUT" \
      "$VALIDATE_OUT" "none (no recognized fixable cause)" "still_invalid"
    ev watchdog.config_invalid_unrecognized detail="$VALIDATE_OUT"
  fi
fi

# 1) gateway responsiveness (consensus: 2 consecutive misses → restart) — F4
if timeout 35 openclaw cron list >/dev/null 2>&1; then
  echo 0 > "$GW_FAILS"
else
  n=$(( $(cat "$GW_FAILS" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$GW_FAILS"
  echo "watchdog: gateway unresponsive (consecutive=$n)"
  if [ "$n" -ge 2 ]; then
    if [ "$SELF_HEAL_MODE" = "L1" ]; then
      record_action "F4_scheduler_dead" "🔎 [L1 report-only] gateway hung (${n}× consecutive) — NOT restarted (mode=L1)" \
        "openclaw cron list timeout, consecutive=$n" "none (L1 report-only mode)" "still_unresponsive"
    else
      openclaw gateway restart >/dev/null 2>&1
      GWVERIFY=$(wait_for_gateway_ready)
      record_action "F4_scheduler_dead" "🔁 gateway hung (${n}× consecutive) → restart ($GWVERIFY)" \
        "openclaw cron list timeout, consecutive=$n" "openclaw gateway restart" "$GWVERIFY"
    fi
    echo 0 > "$GW_FAILS"
    ev watchdog.restart target=gateway consecutive="$n"
  fi
fi

# 2) heartbeat stuck (status=running with stale ts)
CS="$ANICCA_HOME/workspace/core-status.json"
if [ -f "$CS" ]; then
  read -r STATUS CTS < <(python3 - "$CS" <<'PY'
import json,sys,time,calendar
try:
    d=json.load(open(sys.argv[1])); ts=d.get("ts","")
    try: e=calendar.timegm(time.strptime(ts,"%Y-%m-%dT%H:%M:%SZ"))
    except: e=0
    print(d.get("status",""), e)
except Exception:
    print("", 0)
PY
)
  if [ "${STATUS:-}" = "running" ] && [ "${CTS:-0}" -gt 0 ]; then
    age=$(( NOW - CTS ))
    if [ "$age" -gt 1500 ]; then   # >25min running = stuck
      record_action "F4_scheduler_dead" "⚠️ heartbeat stuck in 'running' ${age}s (>25m) — beat likely hung" \
        "core-status.json status=running age=${age}s" "none (informational; check #1/#4 own the restart decision)" "still_stuck"
      ev watchdog.heartbeat_stuck age_s="$age"
    fi
  fi
fi

# 3) peer-api .alive stale + process gone → reload
AL="$ANICCA_HOME/workspace/ops/.alive"
if [ -f "$AL" ]; then
  amod=$(stat -f %m "$AL" 2>/dev/null || echo "$NOW")
  if [ $(( NOW - amod )) -gt 2700 ] && ! pgrep -f "anicca-peer-revive/agent-api.py" >/dev/null 2>&1; then
    if [ "$SELF_HEAL_MODE" = "L1" ]; then
      record_action "peer_api_dead" "🔎 [L1 report-only] peer-api .alive stale + process gone — NOT kickstarted (mode=L1)" \
        ".alive stale $(( NOW - amod ))s + process gone" "none (L1 report-only mode)" "still_dead"
    else
      launchctl kickstart -k "gui/$(id -u)/com.anicca.peer-api" >/dev/null 2>&1 || true
      sleep 5
      PAVERIFY="kickstarted_unconfirmed"; pgrep -f "anicca-peer-revive/agent-api.py" >/dev/null 2>&1 && PAVERIFY="kickstarted_verified"
      record_action "peer_api_dead" "🔁 peer-api .alive stale + process gone → $PAVERIFY" \
        ".alive stale $(( NOW - amod ))s + process gone" "launchctl kickstart com.anicca.peer-api" "$PAVERIFY"
    fi
    ev watchdog.restart target=peer-api
  fi
fi

# 4) scheduler FROZEN — gateway answers cron.list but isn't FIRING (the 2026-06-25
#    1-day outage: SQLite corruption froze nextWakeAtMs ~23h in the past + left 50
#    jobs stuck 'running', while check #1 still passed). Consensus 2 → restart.
SCHED_FAILS="$ST/watchdog-sched-fails"
NOWMS=$(( NOW * 1000 ))
# openclaw_json() (self-heal-lib.sh) strips the intermittent "Config warnings: ..."
# banner `openclaw` sometimes prints to STDOUT before real JSON — found live 2026-07-04
# building TIER 2 (a `cron get`/`cron list --json` call during that work returned the
# banner + JSON glued together, which is NOT valid JSON; python's try/except below then
# silently fell into its `except: print(0)` fallback). Since this check's own comment
# already anticipated "config-warning preamble" as a KNOWN intermittent risk, route
# both calls through the hardened helper instead of raw `openclaw | python3`.
NEXTWAKE=$(openclaw_json cron status | python3 -c "import json,sys
try: print(int(json.load(sys.stdin).get('nextWakeAtMs',0)))
except: print(0)" 2>/dev/null || echo 0)
STUCK=$(openclaw_json cron list --json | python3 -c "import json,sys,time
try:
    d=json.load(sys.stdin); now=int(time.time()*1000)
    print(sum(1 for j in d['jobs'] if j.get('status')=='running' and (now-(j.get('state',{}).get('runningAtMs') or now))>1800000))
except: print(0)" 2>/dev/null || echo 0)
# sanitize to a single clean integer — the raw output can carry config-warning preamble
# or a doubled "0\n0", which made line ~99 error every run and killed this whole check.
NEXTWAKE=$(printf '%s' "$NEXTWAKE" | tr -cd '0-9'); NEXTWAKE=${NEXTWAKE:-0}
STUCK=$(printf '%s' "$STUCK" | tr -cd '0-9'); STUCK=${STUCK:-0}
if { [ "${NEXTWAKE:-0}" -gt 0 ] && [ $(( NOWMS - NEXTWAKE )) -gt 3600000 ]; } || [ "${STUCK:-0}" -ge 15 ]; then
  n=$(( $(cat "$SCHED_FAILS" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$SCHED_FAILS"
  echo "watchdog: scheduler frozen signal (consecutive=$n, overdue=$(( (NOWMS-NEXTWAKE)/60000 ))min, stuck=$STUCK)"
  if [ "$n" -ge 2 ]; then
    if [ "$SELF_HEAL_MODE" = "L1" ]; then
      record_action "F4_scheduler_dead" "🔎 [L1 report-only] scheduler FROZEN (nextWake $(( (NOWMS-NEXTWAKE)/3600000 ))h overdue, ${STUCK} stuck-running) — NOT restarted (mode=L1)" \
        "nextWakeAtMs overdue=$(( (NOWMS-NEXTWAKE)/60000 ))min stuck=$STUCK" "none (L1 report-only mode)" "still_frozen"
    else
      openclaw gateway restart >/dev/null 2>&1
      GWVERIFY=$(wait_for_gateway_ready)
      record_action "F4_scheduler_dead" "🧊 scheduler FROZEN (nextWake $(( (NOWMS-NEXTWAKE)/3600000 ))h overdue, ${STUCK} stuck-running) → gateway restart ($GWVERIFY)" \
        "nextWakeAtMs overdue=$(( (NOWMS-NEXTWAKE)/60000 ))min stuck=$STUCK" "openclaw gateway restart" "$GWVERIFY"
    fi
    echo 0 > "$SCHED_FAILS"
    ev watchdog.restart target=scheduler_frozen
  fi
else
  echo 0 > "$SCHED_FAILS"
fi

# 5) gateway state DB corruption (ROOT CAUSE of the 2026-06-25 outage). quick_check is a
#    safe read on the live WAL db. Consensus 3 (15min) before the destructive auto-recover.
DB="$ANICCA_HOME/state/openclaw.sqlite"
if [ -f "$DB" ] && command -v sqlite3 >/dev/null 2>&1; then
  IC=$(sqlite3 "$DB" "PRAGMA quick_check;" 2>&1 | head -1)
  if [ "$IC" != "ok" ]; then
    DBN=$(( $(cat "$ST/watchdog-db-fails" 2>/dev/null || echo 0) + 1 )); echo "$DBN" > "$ST/watchdog-db-fails"
    echo "watchdog: openclaw.sqlite quick_check != ok (consecutive=$DBN): $IC"
    if [ "$DBN" -ge 3 ]; then
      if [ "$SELF_HEAL_MODE" = "L1" ]; then
        record_action "db_corruption" "🔎 [L1 report-only] openclaw.sqlite CORRUPT (quick_check=$IC) — NOT auto-recovered (mode=L1, destructive action withheld)" \
          "quick_check=$IC consecutive=$DBN" "none (L1 report-only mode)" "still_corrupt"
      else
        TS2=$(date +%Y%m%d-%H%M%S)
        launchctl bootout "gui/$(id -u)/ai.openclaw.gateway" 2>/dev/null || true; sleep 3
        cp "$DB" "$DB.corrupt-$TS2" 2>/dev/null || true
        if sqlite3 "$DB" ".recover" 2>/dev/null | sqlite3 "$DB.rec-$TS2" 2>/dev/null \
           && [ "$(sqlite3 "$DB.rec-$TS2" 'PRAGMA integrity_check;' 2>&1 | head -1)" = "ok" ]; then
          rm -f "$DB-wal" "$DB-shm"; mv "$DB" "$DB.corrupt-replaced-$TS2"; mv "$DB.rec-$TS2" "$DB"
          record_action "db_corruption" "🛠️ openclaw.sqlite CORRUPT → auto-recovered via .recover + gateway restarted" \
            "quick_check=$IC consecutive=$DBN" ".recover + replace + gateway restart" "recovered"
          ev watchdog.db_recover
        else
          rm -f "$DB.rec-$TS2" 2>/dev/null || true
          record_action "db_corruption" "🚨 openclaw.sqlite CORRUPT and auto-recover FAILED — MANUAL FIX NEEDED" \
            "quick_check=$IC consecutive=$DBN" ".recover attempted, failed" "still_corrupt"
        fi
        launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/ai.openclaw.gateway.plist" 2>/dev/null || true
      fi
      echo 0 > "$ST/watchdog-db-fails"
    fi
  else
    echo 0 > "$ST/watchdog-db-fails"
  fi
fi

# 6) MEMORY PRESSURE — gateway RSS growth stalls the event loop → the "unresponsive"
#    restart loop (gateway.log showed rss up to 1.3GB near the heap threshold). A proactive
#    graceful restart BEFORE it hangs is cheaper than a hung-gateway outage. Consensus 2.
MEM_FAILS="$ST/watchdog-mem-fails"
GWPID=$(pgrep -f "openclaw/dist/index.js gateway" | head -1)
if [ -n "${GWPID:-}" ]; then
  RSS_KB=$(ps -o rss= -p "$GWPID" 2>/dev/null | tr -cd '0-9'); RSS_MB=$(( ${RSS_KB:-0} / 1024 ))
  if [ "$RSS_MB" -gt 1200 ]; then
    mn=$(( $(cat "$MEM_FAILS" 2>/dev/null || echo 0) + 1 )); echo "$mn" > "$MEM_FAILS"
    echo "watchdog: gateway RSS ${RSS_MB}MB > 1200MB (consecutive=$mn)"
    if [ "$mn" -ge 2 ]; then
      echo 0 > "$MEM_FAILS"
      if [ "$SELF_HEAL_MODE" = "L1" ]; then
        record_action "gateway_memory_pressure" "🔎 [L1 report-only] gateway RSS ${RSS_MB}MB > 1200MB (2× consecutive) — NOT restarted (mode=L1)" \
          "RSS=${RSS_MB}MB consecutive=$mn" "none (L1 report-only mode)" "still_high"
      else
        openclaw gateway restart >/dev/null 2>&1 || true
        GWVERIFY=$(wait_for_gateway_ready)
        record_action "gateway_memory_pressure" "🧠 gateway RSS ${RSS_MB}MB > 1200MB (2× consecutive) → graceful restart ($GWVERIFY)" \
          "RSS=${RSS_MB}MB consecutive=$mn" "openclaw gateway restart" "$GWVERIFY"
      fi
      ev watchdog.restart target=gateway_memory rss_mb="$RSS_MB"
    fi
  else
    echo 0 > "$MEM_FAILS"
  fi
else
  # gateway process not found this run (e.g. mid-restart from another check) — don't
  # count this as a memory-pressure hit, but don't silently keep a stale counter either.
  echo 0 > "$MEM_FAILS"
fi

finish_and_escalate "all healthy (config ok, gateway ok, heartbeat ${STATUS:-?}, peer-api ok, scheduler ok, db ok, mem ${RSS_MB:-?}MB)"
