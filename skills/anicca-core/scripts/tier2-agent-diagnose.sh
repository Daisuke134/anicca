#!/usr/bin/env bash
# tier2-agent-diagnose.sh — TIER 2 (agent-diagnosis) + F6 (model failover) + TIER 3
# (bounded single-Telegram escalation), spec 2026-07-01-openclaw-self-heal-design.md §3
# + §6.1 (2026-07-04 safety addendum).
#
# F6 (model/provider outage) IS a deterministic decision-table row (spec §3.2: probe =
# ping/lastError pattern, remediation = failover to a known-free model) — handled here
# rather than in tier1-remediate.sh because it needs `openclaw cron`/config access, not
# just log-file scanning.
#
# TIER 2 (genuinely unknown failures — anything NOT explained by F1-F6) is where
# building-effective-ai-agents.md's rule actually applies: the DIAGNOSIS is done by a
# real agent turn reading ground truth (error text, cron definition), not a hardcoded
# regex classifier guessing root cause. Only the DISPATCH decision ("is this F1-F6 or
# genuinely unknown") is deterministic string-matching — that's a machine-format
# classification (does this error contain 'Cannot find package'?), not open-ended
# judgment, and is explicitly allowed by the same rule ("regex is fine for genuine
# parsing of a fixed machine format... not judgment").
#
# ★ SAFETY (spec §6.1, added after discovering 70/200 real crons in error state, mostly
#   content-posting/distribution jobs like Larry/Comedy/Life-call): NEITHER F6 NOR
#   TIER 2 EVER force-fires a cron to "verify" a fix. `openclaw cron run` would actually
#   execute that cron's real payload — for a posting cron, that means a REAL post/send,
#   directly violating "never test by direct posting" (memory
#   feedback_never_test_by_direct_posting). Every fix here is verified by WAITING for
#   the cron's own next NATURALLY SCHEDULED fire and checking its result afterward, on a
#   LATER run of this same script — never forced early. ★
#
# TIER 2's diagnosis agent turn is prompted to be READ-ONLY-DIAGNOSIS-ONLY (may take a
# narrow, safe, infra-level action like a gateway restart; must NEVER execute the
# target cron's own task).
set -uo pipefail
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$ANICCA_HOME/.env" 2>/dev/null || true
ST="$ANICCA_HOME/state"; mkdir -p "$ST"
NOW=$(date +%s)
TIER=2
. "$ANICCA_HOME/skills/_shared/scripts/self-heal-lib.sh"

LOCK="$ST/tier2-agent-diagnose.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -f "$LOCK/pid" ] && kill -0 "$(cat "$LOCK/pid" 2>/dev/null)" 2>/dev/null; then
    echo "tier2: another instance running (pid $(cat "$LOCK/pid")) — skipping this run"; exit 0
  fi
  rm -rf "$LOCK"; mkdir "$LOCK" 2>/dev/null || { echo "tier2: cannot acquire lock — skipping"; exit 0; }
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT

PENDING_DIR="$ST/tier2-pending"; mkdir -p "$PENDING_DIR"
MAX_ATTEMPTS_BEFORE_ESCALATE="${SELF_HEAL_TIER2_MAX_ATTEMPTS:-2}"
MAX_AGENT_DIAGNOSES_PER_PASS="${SELF_HEAL_TIER2_MAX_AGENT_DIAGNOSES_PER_PASS:-1}"
case "$MAX_AGENT_DIAGNOSES_PER_PASS" in
  ''|*[!0-9]*|0) echo "tier2: invalid MAX_AGENT_DIAGNOSES_PER_PASS" >&2; exit 2 ;;
esac
AGENT_DIAGNOSES_THIS_PASS=0
TIER2_AGENT_RUNNER="${TIER2_AGENT_RUNNER:-$SCRIPT_DIR/tier2-run-diagnosis.sh}"
CRON_CONTEXT_MAX_BYTES=16000
STATUS_CONTEXT_MAX_BYTES=12000
LOG_CONTEXT_MAX_BYTES=30000

# is_f1_to_f5 <error_text> -> 0 if it matches a TIER0/TIER1-owned pattern (skip here;
# that tier already owns detecting+fixing it), 1 otherwise. Uses the SAME shared
# predicates tier1-remediate.sh uses (self-heal-lib.sh) — this file used to
# hand-duplicate a less-refined copy (adversary finding, TIER 2, 2026-07-04: no
# zsh-format handling, no shell-name denylist), which is exactly the DRY-violation
# shape self-heal-lib.sh exists to prevent.
is_f1_to_f5() {
  is_dep_missing_error "$1" && return 0
  is_binary_missing_error "$1" && return 0
  is_config_invalid_error "$1" && return 0
  return 1
}
# is_f6 <error_text> -> 0 if it matches a known model/provider-outage signature.
is_f6() { is_model_provider_outage_error "$1"; }

# ===================================================================================
# PASS 1 — check previously-diagnosed (TIER2) jobs whose next scheduled fire has
# already passed: did it resolve itself, or is it still broken? (TIER 3 escalation
# lives here: bounded attempts, then exactly one Telegram message.)
# ===================================================================================
for MARKER in "$PENDING_DIR"/*.json; do
  [ -f "$MARKER" ] || continue
  JOB_ID=$(basename "$MARKER" .json)
  NEXT_RUN_AT_MS=$(python3 -c "import json;print(json.load(open('$MARKER')).get('next_run_at_ms',0))" 2>/dev/null || echo 0)
  # LAST_RUN_AT_MS_AT_DIAGNOSIS: the job's lastRunAtMs AS OF diagnosis time, not just
  # its (possibly stale/zero/confused) nextRunAtMs. Comparing against THIS is what
  # actually proves "a genuinely new run happened since we diagnosed it" — adversary
  # finding, TIER 2, 2026-07-04: relying on nextRunAtMs alone meant a job with a
  # stale/zero nextRunAtMs field (plausible for exactly the "genuinely confused
  # scheduling" failures this tier exists to handle) could have its ORIGINAL
  # diagnosis-triggering failing run miscounted as a brand-new natural retry, on the
  # very next cycle, with zero actual retries having happened.
  LAST_RUN_AT_DIAGNOSIS_MS=$(python3 -c "import json;print(json.load(open('$MARKER')).get('last_run_at_diagnosis_ms',0))" 2>/dev/null || echo 0)
  ATTEMPTS=$(python3 -c "import json;print(json.load(open('$MARKER')).get('attempts',0))" 2>/dev/null || echo 0)
  JOB_NAME=$(python3 -c "import json;print(json.load(open('$MARKER')).get('job_name',''))" 2>/dev/null || echo "")
  NOWMS=$(( NOW * 1000 ))
  [ "${NEXT_RUN_AT_MS:-0}" -gt 0 ] && [ "$NOWMS" -lt "$NEXT_RUN_AT_MS" ] && continue  # scheduled fire hasn't happened yet — nothing to check

  CUR=$(openclaw_json cron get "$JOB_ID")
  if [ -z "$CUR" ]; then
    # job no longer exists (deleted, or a one-shot that cleaned itself up) — nothing
    # left to track. Adversary finding, TIER 2, 2026-07-04: previously this `continue`d
    # WITHOUT removing the marker, leaving an orphan re-checked forever.
    ledger "unknown_diagnosed" "job=$JOB_NAME id=$JOB_ID" "TIER2 diagnosis (see earlier ledger line)" "job_no_longer_exists" "false"
    rm -f "$MARKER"
    continue
  fi
  CUR_STATUS=$(printf '%s' "$CUR" | python3 -c "import json,sys;print(json.load(sys.stdin).get('state',{}).get('lastRunStatus',''))" 2>/dev/null)
  CUR_LAST_RUN_MS=$(printf '%s' "$CUR" | python3 -c "import json,sys;print(json.load(sys.stdin).get('state',{}).get('lastRunAtMs',0))" 2>/dev/null || echo 0)

  if [ "$CUR_LAST_RUN_MS" -le "$LAST_RUN_AT_DIAGNOSIS_MS" ] 2>/dev/null; then
    # no NEW run since diagnosis yet, regardless of what nextRunAtMs claims — leave the
    # marker, re-check later. This is the fix for the stale/zero-nextRunAtMs bug above.
    continue
  fi

  if [ "$CUR_STATUS" = "ok" ]; then
    # a genuinely new run happened since diagnosis AND it succeeded — resolved. Plain
    # ledger(), no escalation: a resolved incident is informational, not alert-worthy.
    ledger "unknown_diagnosed" "job=$JOB_NAME id=$JOB_ID" "TIER2 diagnosis (see earlier ledger line)" "resolved_after_natural_run" "false"
    rm -f "$MARKER"
  else
    # a genuinely new run happened since diagnosis and it STILL errored.
    ATTEMPTS=$(( ATTEMPTS + 1 ))
    if [ "$ATTEMPTS" -ge "$MAX_ATTEMPTS_BEFORE_ESCALATE" ]; then
      # TIER 3 — the ONLY escalation-worthy event for this job. escalation_key is
      # deliberately DISTINCT from the "just diagnosed" event below (adversary finding,
      # TIER 2, 2026-07-04: sharing one key meant the FIRST-EVER diagnosis of a job
      # already escalated immediately — proven live, self-heal-ledger.jsonl, the real
      # larry-en-female-reel-replace-3 incident's initial pending_next_scheduled_run
      # line had escalated:true — violating "bounded attempts, THEN exactly one
      # Telegram message" and risking the cooldown silently swallowing THIS, the
      # actually-urgent message, if it landed within 24h of that harmless first ping).
      record_action "unknown_diagnosed_tier3_escalation" "🚨 [TIER3] '$JOB_NAME' still failing after $ATTEMPTS TIER2 diagnosis+natural-retry cycles — MANUAL FIX NEEDED. Last status: $CUR_STATUS" \
        "job=$JOB_NAME id=$JOB_ID attempts=$ATTEMPTS" "TIER2 diagnosis attempted $ATTEMPTS time(s), cron re-ran naturally each time" "still_broken_after_${ATTEMPTS}_attempts" "unknown_tier3_escalation_${JOB_ID}"
      rm -f "$MARKER"
    else
      python3 -c "
import json
d=json.load(open('$MARKER'))
d['attempts']=$ATTEMPTS
d['last_run_at_diagnosis_ms']=$CUR_LAST_RUN_MS  # advance the watermark to THIS run, so
                                                  # the next cycle requires a FURTHER new
                                                  # run, not the same one counted twice
json.dump(d, open('$MARKER','w'))
"
      ledger "unknown_diagnosed" "job=$JOB_NAME id=$JOB_ID attempts=$ATTEMPTS" "TIER2 diagnosis, awaiting next natural retry" "still_broken_will_retry" "false"
    fi
  fi
done

# ===================================================================================
# PASS 2 — new diagnosis: enabled, erroring crons NOT already covered by F1-F6 or an
# active pending marker.
# ===================================================================================
CRON_LIST_JSON=$(openclaw_json cron list --all --json)
if [ -n "$CRON_LIST_JSON" ]; then
  # emit TSV: id<TAB>name<TAB>lastError<TAB>nextRunAtMs<TAB>lastRunAtMs (only enabled+error jobs)
  printf '%s' "$CRON_LIST_JSON" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for j in d.get('jobs', []):
    st = j.get('state', {}) or {}
    if j.get('enabled') and st.get('lastRunStatus') == 'error':
        err = (st.get('lastDiagnostics', {}) or {}).get('summary') or st.get('lastError') or ''
        print('\t'.join([j.get('id',''), j.get('name',''), err.replace('\t',' ').replace(chr(10),' ')[:500], str(st.get('nextRunAtMs',0)), str(st.get('lastRunAtMs',0))]))
" > "$ST/tier2-current-errors.tsv" 2>/dev/null

  while IFS=$'\t' read -r JOB_ID JOB_NAME ERR_TEXT NEXT_RUN_AT_MS LAST_RUN_AT_MS; do
    [ -n "$JOB_ID" ] || continue
    is_f1_to_f5 "$ERR_TEXT" && continue   # TIER 0/1's job
    [ -f "$PENDING_DIR/$JOB_ID.json" ] && continue  # already being tracked

    if is_f6 "$ERR_TEXT"; then
      # F6 — model/provider outage. Deterministic: this system already has a
      # multi-model fallback catalog configured (agents.defaults.models); a cron
      # hitting FallbackSummaryError/cooldown/402/403 means ITS OWN specific model
      # pin (if any) is broken, not that the whole system has no working model.
      # SAFETY: never force-fire to verify (spec §6.1) — defer to the cron's own
      # next natural scheduled run, tracked the same way as TIER 2 below.
      KEY="F6_${JOB_ID}"
      if should_remediate "$KEY"; then
        JOB_MODEL_OVERRIDE=$(openclaw_json cron get "$JOB_ID" | python3 -c "import json,sys;print(json.load(sys.stdin).get('payload',{}).get('model','') or '')" 2>/dev/null)
        if [ -z "$JOB_MODEL_OVERRIDE" ]; then
          # no per-cron override — it already uses agents.defaults.model's own
          # fallback chain, which already failed too (FallbackSummaryError implies
          # ALL attempted models failed). Nothing safe/deterministic left to try —
          # this needs a human to look at provider health system-wide.
          record_action "F6_model_provider_outage" "🚨 '$JOB_NAME' hit a model/provider outage (${ERR_TEXT:0:150}) with NO per-cron override — the system-wide fallback chain itself is exhausted. MANUAL REVIEW NEEDED" \
            "job=$JOB_NAME id=$JOB_ID error=$ERR_TEXT" "none (no per-cron override to change; system fallback chain already exhausted)" "unfixable_no_override" "F6_model_provider_outage_${JOB_ID}"
        else
          record_action "F6_model_provider_outage" "🚨 '$JOB_NAME' pinned model '$JOB_MODEL_OVERRIDE' hit a provider outage (${ERR_TEXT:0:150}) — flagged for manual model-override review (auto-rewrite of a per-cron model pin intentionally NOT automated this pass; see ledger)" \
            "job=$JOB_NAME id=$JOB_ID model=$JOB_MODEL_OVERRIDE error=$ERR_TEXT" "none — flagged only, no auto-rewrite" "flagged_for_review" "F6_model_provider_outage_${JOB_ID}"
        fi
      fi
      continue
    fi

    # genuinely unknown — TIER 2 agent diagnosis.
    if [ "$AGENT_DIAGNOSES_THIS_PASS" -ge "$MAX_AGENT_DIAGNOSES_PER_PASS" ]; then
      continue
    fi
    KEY="unknown_${JOB_ID}"
    should_remediate "$KEY" || continue
    AGENT_DIAGNOSES_THIS_PASS=$(( AGENT_DIAGNOSES_THIS_PASS + 1 ))

    # Deterministically bound model context. The previous agent was allowed to search
    # all session/log trees and returned a 2.2 MB tool transcript for one diagnosis.
    # Keep filesystem discovery outside the model and truncate every source here.
    JOB_CONTEXT=$(openclaw_json cron get "$JOB_ID" | tail -c "$CRON_CONTEXT_MAX_BYTES")
    STATUS_CONTEXT=$(timeout 20 openclaw status 2>&1 | tail -c "$STATUS_CONTEXT_MAX_BYTES")
    LOG_CONTEXT=$(rg -n -F -e "$JOB_ID" -e "$JOB_NAME" /tmp/openclaw/openclaw-*.log 2>/dev/null \
      | tail -n 60 | cut -c 1-2000 | tail -c "$LOG_CONTEXT_MAX_BYTES")

    PROMPT="You are an autonomous self-heal DIAGNOSTIC agent. A scheduled cron job named '$JOB_NAME' (id $JOB_ID) is failing with an error not explained by any known cause (missing npm package, missing binary, invalid config, disk/log bloat, gateway hang, or model-provider outage — all already handled by other tiers).

Error: ${ERR_TEXT:0:800}

EVIDENCE PACKET (complete and bounded; values may be empty):
--- cron record ---
$JOB_CONTEXT
--- OpenClaw status ---
$STATUS_CONTEXT
--- exact job id/name log matches ---
$LOG_CONTEXT
--- end packet ---

YOUR JOB:
1. Diagnose only from the evidence packet above.
2. Do not execute commands, call tools, read files, restart services, or mutate state.
3. ACTION_TAKEN must be 'none'.
4. Reply in EXACTLY this format, nothing else:
DIAGNOSIS: <one paragraph>
ACTION_TAKEN: none
CONFIDENCE: <high|medium|low>"

    AGENT_OUT=$(printf '%s\n' "$PROMPT" | TIER2_JOB_ID="$JOB_ID" timeout 255 "$TIER2_AGENT_RUNNER" 2>&1)
    AGENT_EXIT=$?
    DIAGNOSIS=$(printf '%s' "$AGENT_OUT" | grep -oE "DIAGNOSIS:.*" | head -1)
    ACTION=$(printf '%s' "$AGENT_OUT" | grep -oE "ACTION_TAKEN:.*" | head -1)

    python3 -c "
import json
json.dump({'job_name': '''$JOB_NAME''', 'diagnosed_at_ms': $(( NOW * 1000 )), 'next_run_at_ms': ${NEXT_RUN_AT_MS:-0}, 'last_run_at_diagnosis_ms': ${LAST_RUN_AT_MS:-0}, 'attempts': 0}, open('$PENDING_DIR/$JOB_ID.json', 'w'))
" 2>/dev/null

    if [ "$AGENT_EXIT" -eq 0 ] && [ -n "$DIAGNOSIS" ]; then
      # plain ledger(), NOT record_action() — a fresh diagnosis is informational
      # ("here's what we found, waiting for the natural retry"), not escalation-worthy
      # on its own. Adversary finding, TIER 2, 2026-07-04 (proven live in production):
      # this used to share the SAME escalation_key as the TIER3-exhaustion event below,
      # which meant should_escalate()'s "first use of a key always fires" behavior
      # caused EVERY fresh diagnosis to immediately alert Telegram — the real
      # larry-en-female-reel-replace-3 ledger line had escalated:true on its very first,
      # harmless diagnosis event, and worse, could silently EAT the 24h cooldown window
      # that the actually-urgent TIER3 escalation for the SAME job needed later.
      ledger "unknown_diagnosed" "job=$JOB_NAME id=$JOB_ID error=$ERR_TEXT" "TIER2 agent diagnosis: ${DIAGNOSIS:0:300} :: ${ACTION:-none}" "pending_next_scheduled_run" "false"
      echo "🔎 '$JOB_NAME' unknown failure diagnosed (logged, not escalated — awaiting natural retry): ${DIAGNOSIS:0:200}"
    else
      # the diagnostic mechanism ITSELF failing IS escalation-worthy (distinct key from
      # both the informational diagnosis above and the TIER3-exhaustion event, so none
      # of the three can suppress each other's cooldown for the same job).
      record_action "unknown_diagnostic_call_failed" "🚨 '$JOB_NAME' unknown failure — TIER2 diagnostic agent call itself failed (exit=$AGENT_EXIT) — MANUAL REVIEW NEEDED" \
        "job=$JOB_NAME id=$JOB_ID error=$ERR_TEXT agent_exit=$AGENT_EXIT" "attempted TIER2 agent diagnosis, the diagnostic call itself errored" "diagnostic_call_failed" "unknown_diagnostic_call_failed_${JOB_ID}"
    fi
  done < "$ST/tier2-current-errors.tsv"
  rm -f "$ST/tier2-current-errors.tsv"
fi

finish_and_escalate "no unhandled unknown failures or model-provider outages among enabled crons"
