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
if [ "${CAPAFY_LOOP_REPORTING_PROBE_ONLY:-0}" = "1" ]; then
  printf 'terminal_owner=capafy-builder-handoff.sh agent_telegram=false\n'
  exit 0
fi
RUN_AGENT="$SCRIPT_DIR/../../earn/marketing-engine/run_agent.sh"
LOG="$HOME/.openclaw/logs/capafy-loop-daily.log"
mkdir -p "$(dirname "$LOG")"
echo "=== capafy-loop-daily run $(date '+%F %T %Z') ===" >>"$LOG"

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

PROMPT='You are the Anicca Capafy money-loop core (provider-agnostic, self-improving + self-healing; money → Dais bank; human + main-agent NOT in this loop). This pass was triggered by a real launchd daily schedule (ai.anicca.capafy-loop-daily) — you do NOT need to register your own cron; that is handled outside this process now. STEP0 SELF-HEAL: AUTH-DOWN means ONLY that GET https://api.capafy.ai/agent/account returns HTTP 401 — check THAT first; if it returns 200 the token is VALID and you must NOT re-login. The Capafy marketplace SEARCH endpoint (POST /agent/agents/search) may be BROKEN server-side (returns 500, or a MISLEADING 401 that says token expired, even with a valid token), and re-login just returns the SAME stable am_sk_ api-key so it can NEVER fix a search error — therefore a search failure is NEVER auth-down and NEVER a reason to re-login, retry, or spiral. Only if /agent/account itself is 401: re-login via login-init → read OTP from keiodaisuke@gmail.com via gog gmail (needs GOG_KEYRING_PASSWORD sourced from ~/.openclaw/.env) → login-verify → write token into BOTH vendor/capafy-publisher/config.json and vendor/capafy-user/config.json. If ~/.openclaw/state/capafy-loop-selfheal-request.json exists, read+diagnose+fix then rm it; CAPAFY-LOOP-STALE/NEVER-RAN → run bash ~/.openclaw/skills/capafy-autopublish/scripts/daily_loop.sh; verify heal clears then rm the json; if you cannot fix it in this pass, bash ~/anicca/skills/self/self-fix.sh capafy "<the exact blocker + a concrete fix hint>" to spawn an autonomous high-value dev that actually edits+runs+verifies+commits the code fix (THAT is the self-heal — never just file an issue and wait), then rm the json. STEP1 MEASURE: bash ~/anicca/skills/self/capafy-loop/loop.sh and read its STATE.md. STEP2 ACT (single highest-EV move toward real Capafy revenue; your judgment): FIRST run  /opt/homebrew/bin/python3 ~/anicca/skills/self/capafy-loop/sales_selector.py  and read its JSON (also saved to ~/.openclaw/state/capafy-sales-ranking.json): if signal=sales, build the NEXT skill in the winner category it names (double down on what actually sells for us); if signal=none (no sales yet across our listings), do NOT fabricate a winner — proceed via BEST_PRACTICES marketplace research below. Then improve SUPPLY QUALITY by publishing ONE more competitive, honest, lint-clean listing that PASSES THE RENEWAL GATE below (a listing that fails the renewal gate is not supply, it is dead weight — 27 of ours prove it). Market-search (reading a top seller to clone) is BEST-EFFORT enrichment ONLY: try it at most once, but Capafy search may be server-broken so expect it to fail — if it errors, do NOT retry, re-login, or stop; proceed WITHOUT it using ~/.openclaw/skills/capafy-autopublish/BEST_PRACTICES.md + the proven-profitable playbook + existing inventory. If BEST_PRACTICES.md has not been refreshed with a real external web search in the last 7 days, spend at most one external-research pass on "capafy.ai top selling AI agent skills" or similar and append any genuinely new, verifiable finding to BEST_PRACTICES.md (do not invent claims). Then publish exactly ONE ready item by running the BOUNDED drainer: bash ~/.openclaw/skills/capafy-autopublish/scripts/daily_loop.sh (fail-closed, self-limited, timeout-guarded). If the slot cap is full OR no inventory item is ready (skill dir + icon both present), that is a LEGITIMATE NO-OP — report it and finish the pass cleanly; never hang waiting. If verdict=DRAINED (no publishable item and no fresh inventory), use the rest of this pass to DESIGN and FULLY SUBMIT ONE brand-new, genuinely differentiated skill (not a duplicate of an already-online listing). ★★ RENEWAL GATE — RUN THIS BEFORE YOU WRITE A SINGLE FILE (full text + few-shot examples: BEST_PRACTICES.md section 1b) ★★ The design MUST satisfy BOTH: (R1) RECURRING INPUT — the buyer holds a NEW instance of the input on a fixed daily or weekly schedule and pastes it in themselves; the subject is a repeating EVENT or a moving NUMBER (this week fixtures + team news, today positions or watchlist, this week KOL or timeline posts, this week ad-performance export). The BUYER supplies the fresh data, so we never claim live retrieval and the section-6 honesty rules stay intact; our value is the recurring ANALYSIS, not a fetch. (R2) STALE-IN-A-WEEK OUTPUT — last cycle output is worthless to them this cycle. Then answer literally: on day 8, why has this buyer NOT cancelled? The ONLY passing answer is that a new event or number happened and last week output is now stale. Any answer shaped like they might need another one someday is a FAIL — DISCARD the idea and design a different one; never try to rescue a failing idea by rewriting its copy, because the SHAPE is what is broken. ★ HARD REJECTION: one-shot document generators are FORBIDDEN — performance review, job description, resume, ESG scoping memo, sales-objection sheet, policy, business plan, board deck, speech, or any document a buyer needs once per person or per company. Measured 2026-07-30 live marketplace parse: all 27 of our one-shot B2B doc writers have recentSales=0 and marketplace CVR 0.00 percent, while the top 1 listing takes 57 percent of all 4,889 marketplace sales and every winning vertical is recurring-event data (football fixture analysis 2,788 sold, stock tracking 781 sold at $9.99/week, X/KOL tracking, video generation). The one-shot shape is the defect, not the copy. ★ CHOOSE FROM DEMAND DATA, NOT FROM A GUESS: rank candidate niches by the measured demand you can actually point at — sales_selector when signal=sales, otherwise the measured sold-counts in BEST_PRACTICES sections 10 through 13 — and pick the highest-demand RECURRING-INPUT vertical that is not already in our catalog. Write the gate answer (R1 / R2 / day-8 answer / demand evidence) into the LISTING.md internal notes above the Title section; if you cannot fill in the demand-evidence line with a real observed number, you are guessing — pick a different niche. ★ PACKAGING DEFAULT (references/pricing.md is the SSOT): closed-source run_online Subscription, NEVER Download (Download hands the buyer our source and ends the revenue relationship after one payment); ONE paid week plan at $9.99/week; cap 20; trial choice = No Free Trial (free-trial packaging is 36 of 70 listings but ZERO of the 100-plus-sold tier). Platform floors $2/day, $5/week, $8/month. Net per subscriber = (9.99 minus 0.50 sandbox fee) times 0.80 = $7.59/week, about $32.9/month, so about 304 concurrent weekly subscribers is $10k/month. Deviate only by citing a live winner you actually read. ★ LISTING COPY (references/agent_card_templates.md): the title MUST be KEYWORD-FIRST (open with the subject noun a buyer would type or scan for, then the em-dash benefit; a coined opaque brand loses the scan) and the shortDescription MUST carry ONE concrete, checkable CREDIBILITY PROOF LINE — and that proof MUST BE TRUE, since inventing a credential, employer, view count, or conversion lift is a section-6 honesty violation the linter cannot catch. ★★ Then write its skill dir + LISTING.md + test case + icon, run publish-init, then DRIVE IT ALL THE WAY THROUGH CP1 (agent card: title/short/detailed/welcomeMessage/tags/category/pricing/model/test-input/per-plan trial radios/DPA checkbox — read PUBLISHING_RUNBOOK.md for the complete silent-failure gotcha list) → publish-configure → CP2 (LLM config keys) → publish-ship → CP3 (審査に提出). ★★ A DRAFT IS NOT DONE. A draft earns $0 and occupies a publish-cap slot. The act is only complete when publish-remote-status shows status=1 (under review) + isConfirmedSkills=1 + isConfirmedConfigKeys=1. ★★ You have NO wall-clock limit on this pass (no timeout) — do NOT stop early, do NOT defer work to "tomorrow'"'"'s pass", do NOT leave a half-finished draft behind. If a UI step blocks you, debug it and retry until it actually saves. There is also an existing ORPHAN-DRAFT backlog on the server — resolve those the same way (finish them through CP3, or explicitly abandon them to free the cap slot); never let drafts pile up. STEP3 VERIFY: only a real subscriber or a listing reaching status=4 counts — published alone is NOT revenue; record the observable in STATE.md. IF your ACT fails because of a code/automation bug (e.g. daily_loop.sh reports publish FAIL / drive_cp1.py isConfirmedSkills=0 / any tool error), that is NOT a stop and NOT a defer — immediately bash ~/anicca/skills/self/self-fix.sh capafy "publish pipeline broken: <paste the exact error>. Fix the publisher (likely drive_cp1.py brittle UI automation) so a real skill publishes." and note it in STATE.md. STEP4 REPORT: bash ~/anicca/skills/report/loop-report.sh capafy "<what you did + real metric>" <success|failure|no-op> <usd or 0> "<evidence url or none>". FINALLY — ALWAYS, even on a clean no-op or a caught error — touch ~/.openclaw/state/.capafy-loop-last-pass to prove this pass completed (this is the liveness heartbeat; never leave it un-touched by hanging or spiraling). Blocker is not stop; a broken Capafy endpoint is not stop. STEP5 TELEGRAM REPORT TO DAIS -- MANDATORY, every pass, success or failure: PushNotification does NOT reach Dais (it silently no-ops when Remote Control is inactive -- proven 2026-07-12). Use the channel that actually delivers, the same one connector and gig use: openclaw message send --channel telegram --target 8547730585 --message "<your honest one-screen report>" --json. The message MUST contain: what you actually did this pass, the agent_id and its real remote status (status/isConfirmedSkills/isConfirmedConfigKeys read back from publish-remote-status -- never a claim without the readback), how many listings are online, and the honest revenue figure (say $0 if it is $0 -- never inflate). Confirm the send returned a real message id; if the send fails, retry once and then note the failure in STATE.md.'

# ★★ BUDGET SPLIT (self-fix-capafy-loop, 2026-07-30) ★★
# The prompt above orders BOTH orphan-resolution AND new-skill design with no budget
# split, so ONE stuck orphan ate 100% of every pass: draft 9470213182 (isConfirmedSkills=1,
# isConfirmedConfigKeys=0) blocked the loop from 2026-07-27 and NO new skill shipped for
# three days. Fix = a HARD wall-clock split injected as DATA (absolute unix deadlines the
# model checks with `date +%s`), not a polite request. Orphan work gets ~1/3 of the pass;
# the remainder is RESERVED for new-skill design and the model must switch even mid-repair.
LANE_SECONDS="${CAPAFY_LANE_SECONDS:-3600}"
PASS_START="$(date +%s)"
PASS_DEADLINE=$(( PASS_START + LANE_SECONDS - 120 ))      # leave 120s for STEP4/STEP5
ORPHAN_DEADLINE=$(( PASS_START + LANE_SECONDS / 3 ))      # ~1/3 of the pass
PROMPT="$PROMPT
★★ PASS BUDGET — THIS SECTION OVERRIDES THE 'NO wall-clock limit' TEXT ABOVE ★★
This pass started at unix $PASS_START and is SIGKILLed at unix $PASS_DEADLINE. Read the
clock with \`date +%s\` and treat these as hard walls:
  · PHASE A (orphan/backlog repair) ends at unix $ORPHAN_DEADLINE — about one third of the pass.
  · PHASE B (new skill) owns unix $ORPHAN_DEADLINE .. $PASS_DEADLINE and is NEVER skipped.
PHASE A — repair the oldest blocking draft ONLY. The moment \`date +%s\` passes
$ORPHAN_DEADLINE you MUST stop touching orphans, even mid-repair, even if one more click
feels like it would finish it. Stopping loses NOTHING: every checkpoint lives on the server
and is idempotent (isConfirmedSkills / isConfirmedConfigKeys / status), and publish_finish.sh
skips any step already confirmed, so the next pass resumes exactly where you stopped. Before
leaving Phase A, write the orphan's agent_id plus its real readback into STATE.md.
★ If the SAME orphan has consumed 3+ passes without its server fields moving, STOP repairing
it and ABANDON it explicitly to free the publish-cap slot — a draft that cannot be confirmed
is worth less than the slot it occupies. Report that you abandoned it and why. A one-shot
document generator (performance review, job description, resume, memo, policy, business plan)
is a HARD-REJECTION shape under the renewal gate, so finishing it would only create dead
weight — abandon those on sight instead of repairing them.
PHASE B — MANDATORY: design and FULLY SUBMIT one brand-new skill that PASSES THE RENEWAL
GATE above (that gate is not optional and must not be weakened). A pass that reaches
$PASS_DEADLINE with zero new listings submitted is a FAILED pass and you must say so
honestly in STEP4/STEP5 instead of reporting orphan work as success.
★ CP2 IS NO LONGER A ONE-SHOT ★ drive_checkpoint2.py now runs a bounded
observe/act/re-observe loop and exits 2 = NEEDS_AGENT when the server field has not flipped.
On exit 2 do NOT re-run it unchanged and do NOT spiral: read
~/.openclaw/skills/capafy-autopublish/CP2_AGENTIC.md and finish CP2 AGENTICALLY with
scripts/cp2_agent.py — open the page, screenshot, LOOK at it, decide the next click/fill,
re-observe, and verify with \`cp2_agent.py confirmed <agent_id>\` until the server itself
reports isConfirmedConfigKeys=1. A toast is only a hint; the server field is the truth.
★ BROWSER: never hardcode a CDP port and never close/kill the daily-driver. Lease it with
\`~/.config/ai/bin/browser-guard.sh acquire interactive:dais\` (exit 9 = BUSY is NORMAL —
skip the browser work this pass and say so), and release it when done."

EVIDENCE_DIR="$HOME/.openclaw/state/agent-runner-evidence/capafy-marketplace/$(date +%s)-$$"
BUILDER_RESULT="${CAPAFY_BUILDER_RESULT:-$HOME/.openclaw/state/capafy-builder-result.json}"
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
# task-class application-lane-agent (3600s), NOT browser-lane-agent (900s).
# WHY THE RAISE (and not "make orphan work resumable"): orphan work is ALREADY resumable —
# every CP1/CP2/CP3 checkpoint is server-side and idempotent and publish_finish.sh skips
# whatever is already confirmed — so a 900s cut was never losing state, it was simply
# never enough clock for THREE sequential browser checkpoints plus a skill design in one
# pass. Measured: 4 consecutive passes (2026-07-24..28) died at duration_ms 900044 with
# timed_out:true and real progress on stdout, and a READ-ONLY dry run alone took 229s.
# application-lane-agent already exists at 3600s (agent-runner/config.json), so this is an
# existing lane being reused, not a new knob. The Phase A/B budget split above is what
# guarantees the extra clock reaches new-skill design instead of feeding a stuck orphan.
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
