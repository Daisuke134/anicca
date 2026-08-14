#!/usr/bin/env bash
# capafy-loop-daily.sh — DETERMINISTIC daily trigger for the Capafy money loop (Dais 2026-07-12:
# found via live audit that the tmux STARTUP prompt's self-registered `CronCreate "0 9 * * *"` never
# actually persisted anywhere on this machine — no cron store, no second daily run, tmux session sat
# idle for 19h+ after its one manual pass on 2026-07-11. Root cause: an in-session CronCreate call from
# an in-session model/tmux process is not a real OS/gateway scheduler. Fix = same pattern already proven
# for connector (connector_fill_gaps.sh + launchd StartCalendarInterval): launchd calls THIS script
# directly, once a day, bounded + timeout-guarded, no reliance on the LLM self-scheduling itself.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECOVERY_CONTRACT='KNOWN CAPAFY RECOVERY — deterministic, no human and no generic self-fix:
1. If whole-browser Playwright reaches "ws connected" and then times out, keep the browser lease and use ~/.openclaw/skills/capafy-autopublish/scripts/capafy_target_cdp.py with the exact temporary-link token. Read state and act only on that one /devtools/page target. Never retry whole-browser attachment, pick the last Capafy tab, or close unrelated tabs.
2. For an isolated publish profile, OPENCLAW_CONFIG_PATH and OPENCLAW_STATE_DIR must point to the same isolated profile root: export OPENCLAW_CONFIG_PATH="$PROFILE_ROOT/openclaw.json" and OPENCLAW_STATE_DIR="$PROFILE_ROOT", and use runtime_dir "$PROFILE_ROOT/workspace". Before CP2, require credential_counts.generic=0 and the intended official provider url_proxy; if not, stop before any remote credential confirmation and repair the profile binding.'
if [ "${CAPAFY_LOOP_RECOVERY_PROBE_ONLY:-0}" = "1" ]; then
  printf '%s\n' "$RECOVERY_CONTRACT"
  exit 0
fi
if [ "${CAPAFY_LOOP_REPORTING_PROBE_ONLY:-0}" = "1" ]; then
  printf 'terminal_owner=capafy-builder-handoff.sh agent_telegram=false\n'
  exit 0
fi
RUN_AGENT="${CAPAFY_RUN_AGENT:-$SCRIPT_DIR/../../earn/marketing-engine/run_agent.sh}"
PUBLISH_LIST="${CAPAFY_PUBLISH_LIST:-$HOME/.openclaw/skills/capafy-autopublish/vendor/capafy-publisher/packager.py}"
LOG="$HOME/.openclaw/logs/capafy-loop-daily.log"
mkdir -p "$(dirname "$LOG")"
echo "=== capafy-loop-daily run $(date '+%F %T %Z') ===" >>"$LOG"

BUILDER_RESULT="${CAPAFY_BUILDER_RESULT:-$HOME/.openclaw/state/capafy-builder-result.json}"
RECONCILE_LEDGER="${CAPAFY_RECONCILE_LEDGER:-$SCRIPT_DIR/state/capafy-earn-ledger.jsonl}"
RECONCILE_ARGS=(--ledger "$RECONCILE_LEDGER")
if [ "${CAPAFY_TEST:-0}" = "1" ]; then
  RECONCILE_ARGS+=(--sales-json "${CAPAFY_FIXTURE:-/nonexistent}/cap_trend.json" --payout-json "${CAPAFY_FIXTURE:-/nonexistent}/cap_payout.json")
else
  RECONCILE_ARGS+=(--backfill)
fi
if ! python3 "$SCRIPT_DIR/capafy_earn_reconcile.py" "${RECONCILE_ARGS[@]}" >>"$LOG" 2>&1; then
  echo "=== capafy-loop-daily blocked: authoritative reconcile failed ===" >>"$LOG"
  exit 1
fi
CAPACITY_CONSTRAINT=""
if [ ! -f "$PUBLISH_LIST" ]; then
  echo "=== capafy-loop-daily blocked: publisher inventory command is missing ===" >>"$LOG"
  exit 1
fi
if ! INVENTORY_READBACK="$(cd "$(dirname "$PUBLISH_LIST")" && python3 "$PUBLISH_LIST" publish-list 2>>"$LOG")"; then
  echo "=== capafy-loop-daily blocked: inventory status read failed ===" >>"$LOG"
  exit 1
fi
if ! INVENTORY_COUNTS="$(printf '%s' "$INVENTORY_READBACK" | python3 -c 'import json,sys
a=json.load(sys.stdin)["agents"]["list"]
assert isinstance(a,list) and all(type(x.get("hasOnlineVersion")) is bool for x in a)
count=lambda status: sum(x.get("agentStatus")==status for x in a)
print(len(a),count("online"),count("review_rejected"),count("draft"),sum(not x["hasOnlineVersion"] for x in a),sep="\t")' 2>>"$LOG")"; then
  echo "=== capafy-loop-daily blocked: inventory status is malformed ===" >>"$LOG"
  exit 1
fi
IFS=$'\t' read -r INVENTORY_TOTAL ONLINE_COUNT REJECTED_COUNT DRAFT_COUNT NEVER_ONLINE_COUNT <<<"$INVENTORY_COUNTS"
unset CAPAFY_BLOCK_NEW_AGENT
if [ "$NEVER_ONLINE_COUNT" -ge 5 ]; then
  export CAPAFY_BLOCK_NEW_AGENT=1
  CAPACITY_CONSTRAINT="FIRST-VERSION REVIEW QUEUE FULL — never_online=$NEVER_ONLINE_COUNT, total=$INVENTORY_TOTAL, online=$ONLINE_COUNT, review_rejected=$REJECTED_COUNT, draft=$DRAFT_COUNT. New addAgent creation is forbidden this pass; addAgentVersion for an existing agent_id remains allowed. Reconciliation and authenticated inventory refresh completed; continue STEP1/STEP2 and choose one bounded highest-EV review repair, measurement, optimization, Marketing handoff, or truthful no-op."
  echo "=== capafy-loop-daily continuing with first-version queue full (never_online=$NEVER_ONLINE_COUNT) ===" >>"$LOG"
fi

# ── TOKEN BUDGET BREAKER (2026-07-30) ─────────────────────────────────────────
# Every pass of this loop used to record {"status":"disabled","reason":
# "budget_not_configured"} in its attempts.jsonl: the runner's breaker only arms
# when ANICCA_BUDGET_SCOPE_ID + ANICCA_PASS_TOKEN_BUDGET +
# ANICCA_LOOP_DAILY_TOKEN_BUDGET are ALL exported together
# (agent_runner.py:947-955). Unarmed, a spiralling pass has no ceiling at all.
# SIZING is from measured charged tokens in
# ~/.openclaw/state/agent-runner-evidence/capafy-marketplace/*/attempts.jsonl
# (codex charge = total_tokens - cached_input_tokens, agent_runner.py:196-212):
# 5 passes, peak 6,434,708, mean 1,340,211. 16Mi per pass ≈ 2.6x the peak, so
# normal work never trips it; 32Mi/day is the runaway breaker across re-fires
# (self-heal can invoke this lane more than once a day).
# ANICCA_BUDGET_DAILY_SCOPE keys the daily pool to THIS LaunchAgent, so the
# drainer's smaller pool is not charged against this pass's spend.
# NOT set: ANICCA_BUDGET_REQUIRED=1 — this is the revenue lane and a missing env
# var must not turn the money loop into a hard refusal; the three exports below
# are unconditional, so the breaker is armed regardless.
export ANICCA_BUDGET_SCOPE_ID="${CAPAFY_LOOP_PASS_ID:-$(date +%s)-$$}"
export ANICCA_PASS_TOKEN_BUDGET="${CAPAFY_LOOP_PASS_TOKEN_BUDGET:-16777216}"
export ANICCA_LOOP_DAILY_TOKEN_BUDGET="${CAPAFY_LOOP_DAILY_TOKEN_BUDGET:-33554432}"
export ANICCA_BUDGET_DAILY_SCOPE="${CAPAFY_LOOP_BUDGET_DAILY_SCOPE:-capafy-loop-daily}"
export ANICCA_TOKEN_BUDGET_LEDGER="${CAPAFY_TOKEN_BUDGET_LEDGER:-$HOME/.local/state/anicca/telemetry/token-budget.jsonl}"

# ── HOST-KEY SPEND SNAPSHOT ───────────────────────────────────────────────────
# Our own passes are $0 marginal (codex on the ChatGPT OAuth subscription). The
# real spend is CAPAFY_HOST_OPENROUTER_KEY, injected as a CP2 hosted config key
# into every published listing, so every SUBSCRIBER run bills us. Snapshot the
# OpenRouter balance each pass so that spend is at least visible in a durable
# jsonl. Non-fatal by design: a credits read failure must never stop the loop.
python3 "$HOME/.openclaw/skills/capafy-autopublish/scripts/host_key_usage_log.py" \
  capafy-loop-daily >>"$LOG" 2>&1 || true

PROMPT="$(cat <<'CAPAFY_PROMPT'
You are the Anicca Capafy money-loop core. This pass is triggered by the real ai.anicca.capafy-loop-daily launchd job; never register another scheduler.
STEP0 AUTH AND RECOVERY: Treat auth as down only when GET https://api.capafy.ai/agent/account returns HTTP 401. A marketplace search failure is not auth failure. If an existing self-heal request exists, diagnose it through the existing Capafy scripts; the deterministic shell caller owns incident creation, repair dispatch, and Telegram.
STEP1 MEASURE: Run bash ~/anicca/skills/self/capafy-loop/loop.sh, read STATE.md, and use the already-reconciled authenticated inventory and money evidence from this pass.
STEP2 ACT: Choose exactly one bounded highest-expected-value action supported by current evidence. Run /opt/homebrew/bin/python3 ~/anicca/skills/self/capafy-loop/sales_selector.py once. Marketplace search is best-effort and may be tried at most once; never retry or reauthenticate because search fails. Reuse the existing publisher, portfolio, packaging, and Marketing commands. Creating a new Agent is allowed only when the first-version queue has an open slot and evidence makes creation the single best action; it is never mandatory.
If the chosen action creates or changes a listing, cite observed demand, use ~/.openclaw/skills/capafy-autopublish/BEST_PRACTICES.md, keep all claims truthful, and complete the existing publish checkpoints through authenticated remote readback. A draft is not a verified submission. Do not assume a purchase model, delivery mode, price, trial, or cap. If the evidence needed for those choices is absent, choose optimize_packaging or no_op instead of inventing a policy.
STEP3 VERIFY: A paid order is revenue only when authoritative money evidence attributes it. A listing action succeeds only when the remote readback proves its actual status and confirmation fields. Record no projected or unverified revenue.
STEP4 TERMINAL: Write only the deterministic result artifact required below. Do not send Telegram or call self-fix directly; the shell caller owns both.
CAPAFY_PROMPT
)"

PROMPT="$PROMPT
$RECOVERY_CONTRACT"

# One bounded action must leave time for deterministic handoff and reporting.
LANE_SECONDS="${CAPAFY_LANE_SECONDS:-3600}"
PASS_START="$(date +%s)"
PASS_DEADLINE=$(( PASS_START + LANE_SECONDS - 120 ))
PROMPT="$PROMPT
PASS BUDGET: This pass started at unix $PASS_START and must finish its one selected action by unix $PASS_DEADLINE so deterministic handoff can run. Existing publisher checkpoints are resumable and idempotent; do not repeat a confirmed remote step. If CP2 reports NEEDS_AGENT, use the existing CP2_AGENTIC.md and cp2_agent.py flow and trust the authenticated server fields, not a toast. Never hardcode a CDP port or close the daily-driver. Lease it with
\`~/.config/ai/bin/browser-guard.sh acquire interactive:dais\` (exit 9 = BUSY is NORMAL —
skip the browser work this pass and say so), and release it when done."

EVIDENCE_DIR="$HOME/.openclaw/state/agent-runner-evidence/capafy-marketplace/$(date +%s)-$$"
BUILDER_RESULT="${CAPAFY_BUILDER_RESULT:-$HOME/.openclaw/state/capafy-builder-result.json}"
CAPAFY_PORTFOLIO="${CAPAFY_PORTFOLIO:-$HOME/.openclaw/state/capafy-portfolio.json}"
CAPAFY_PACKAGING_REMOTE="${CAPAFY_PACKAGING_REMOTE:-$EVIDENCE_DIR/capafy-packaging-remote.json}"
CAPAFY_PACKAGING_DECISION="${CAPAFY_PACKAGING_DECISION:-$EVIDENCE_DIR/capafy-packaging-decision.json}"
CAPAFY_PACKAGING_VALIDATED="${CAPAFY_PACKAGING_VALIDATED:-$EVIDENCE_DIR/capafy-packaging-validated-portfolio.json}"
CAPAFY_PACKAGING_SCRIPT="${CAPAFY_PACKAGING_SCRIPT:-$SCRIPT_DIR/../../earn/capafy-marketing/scripts/capafy_packaging_decision.py}"
export CAPAFY_PORTFOLIO CAPAFY_PACKAGING_REMOTE CAPAFY_PACKAGING_DECISION CAPAFY_PACKAGING_VALIDATED CAPAFY_PACKAGING_SCRIPT
rm -f "$BUILDER_RESULT"
PROMPT="$PROMPT
★★ DETERMINISTIC TERMINAL HANDOFF — THIS OVERRIDES STEP3/STEP5 REPORTING AND SELF-FIX OWNERSHIP ★★
Do not call self-fix and do not send Telegram yourself. The shell caller owns incident identity,
remote verification, money labels, repair dispatch, and Telegram delivery. Before returning, write
exactly one JSON object to $BUILDER_RESULT:
  submitted: {\"result\":\"submitted\",\"agent_id\":\"<id>\",\"listing_url\":\"<real Capafy review URL>\"}
  no-op:     {\"result\":\"no-op\",\"reason\":\"<bounded truthful reason>\"}
  failure:   {\"result\":\"failure\",\"reason\":\"<exact terminal blocker>\"}
Writing submitted is only a candidate claim; the caller independently re-reads Capafy's remote status."
PROMPT="$PROMPT
PACKAGING CONTRACT: optimize_packaging must target one numeric existing agent_id. Read fresh authenticated publish-remote-status into $CAPAFY_PACKAGING_REMOTE, use capafy_packaging_decision_prompt.py with $CAPAFY_PORTFOLIO and that target, and write its exact JSON decision to $CAPAFY_PACKAGING_DECISION. Choose from buyer value shape: recurring changing input = subscription; value proportional to actions/results = usage; one bounded deliverable = one_time; combined recurring and metered/bounded value = hybrid. Validate without changing the live portfolio: python3 $CAPAFY_PACKAGING_SCRIPT --portfolio $CAPAFY_PORTFOLIO --decision $CAPAFY_PACKAGING_DECISION --remote-json $CAPAFY_PACKAGING_REMOTE --output $CAPAFY_PACKAGING_VALIDATED. Every price, unit, fee, model cost, and contribution field needs exact evidence; missing economics must end as no_op or failure, never an injected model or price."
if [ -n "$CAPACITY_CONSTRAINT" ]; then
  PROMPT="$PROMPT
$CAPACITY_CONSTRAINT This trailing constraint overrides any earlier addAgent option. Never omit the existing agent_id when repairing or resubmitting a rejected Agent.
★★ FULL-QUEUE RESULT CONTRACT — OVERRIDES THE GENERIC submitted/no-op EXAMPLES ABOVE ★★
Write result as exactly one of: poll_review, measure, repair_rejected, reposition, retire_candidate, optimize_packaging, handoff_marketing, no_op.
For any action except no_op, write exactly one non-empty target and one evidence-backed reason:
  {\"result\":\"<allowed action>\",\"target\":\"<one agent_id or public listing URL>\",\"reason\":\"<observed result>\"}
For repair_rejected only, also include agent_id equal to target plus its real listing_url; the caller independently verifies the remote submission.
For no_op, omit target and write one explicit bounded reason: {\"result\":\"no_op\",\"reason\":\"<why none of the seven actions is safe now>\"}.
Do not invent another action, executor, service, or command. Use only the existing Capafy commands already named in this prompt."
fi
# Reuse the existing 3600-second application lane; the remote checkpoints are resumable.
printf '%s\n' "$PROMPT" | "$RUN_AGENT" \
  --task-class application-lane-agent \
  --evidence-dir "$EVIDENCE_DIR" \
  --task-label capafy-marketplace-daily \
  --loop capafy >>"$LOG" 2>&1
RC=$?
echo "=== capafy-loop-daily done rc=$RC $(date '+%F %T %Z') ===" >>"$LOG"
touch "$HOME/.openclaw/state/.capafy-loop-last-pass" 2>/dev/null || true
CAPAFY_BUILDER_RESULT="$BUILDER_RESULT" bash "$SCRIPT_DIR/capafy-builder-handoff.sh" "$RC" "$EVIDENCE_DIR" >>"$LOG" 2>&1
exit $?
