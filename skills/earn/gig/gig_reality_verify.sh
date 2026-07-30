#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
# gig_reality_verify.sh — the reality-verifier runner for the gig loop (feature gig-reality-verify,
# 増分2b: docs/loop-engineering/26-gig-loop-asis-tobe-plan.md §8, BP §2/§7 of
# docs/loop-engineering/25-browser-use-verify-selfimprove-bp.md). Called by auditor.sh AFTER its
# existing deterministic verdict, so the gig loop is judged not just by "did files change" but by
# "does the REAL Coconala screen match what the core claimed" — a FRESH, report-independent
# a fresh bounded tool-agent through the common runner does the judging via gig_judge.py's
# report-skeptical prompt, navigating the dedicated Gig CDP runtime in owned hidden targets
# (via the DETERMINISTIC cdp_nav_snapshot.py helper —
# behavioral-spec REQ-006) and reading the real rendered DOM evidence itself.
#
# Fresh-adversary fix round (FIND-002/003, REQ-007/008): this script NEVER accepts the judge's
# self-reported verdict:true on faith — it generates a STABLE pass_id BEFORE spawning the judge,
# embeds it in the prompt, and after the judge returns, runs it through gig_reality_gate.py, which
# deterministically (no LLM) counts the REAL trajectory rows captured for that pass_id during this
# run and downgrades an unbacked verdict:true to false. Report-blind at neither layer.
#
# stdout-JSON-only discipline (memory: feedback_loop_scripts_must_emit_clean_json_stdout): all
# diagnostic/progress text below goes to stderr (>&2); the ONLY thing this script prints to stdout
# is the final structured JSON summary line.
#
# Usage: bash gig_reality_verify.sh [N_recent_rows]   (default N=5 per source file)
set -uo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/gig_paths.sh
source "$SELF_DIR/scripts/gig_paths.sh"
G="$GIG_STATE_DIR"
AUDIT_REALITY="$G/audit-reality.jsonl"
SELFHEAL="$GIG_HOST_STATE_DIR/.gig-core-selfheal-request.json"
PY="$(command -v python3 || echo /opt/homebrew/bin/python3)"
RUNNER="$GIG_RUNNER_DIR/agent_runner.py"
JUDGE_SCHEMA_FILE="$SELF_DIR/schemas/gig_reality_verdict.schema.json"
TRAJECTORY_ROOT="$G/trajectory"
N="${1:-5}"
TIMEOUT_SECS=1200   # cap the fresh judge spawn — never block auditor.sh forever (behavioral-spec REQ-004 edge case).
# Raised 600->900 (2026-07-15, same incident as the --json-schema fix above): the heaviest
# legitimate rounds (10 claims across 4 ground-truth URLs + several talkroom cross-checks) were
# already observed taking up to ~462s under the OLD plain-text judge (realityverify-1784094300-58538,
# spawn-to-recorded elapsed 462s) — close to the 600s cap even before schema enforcement. A live test
# of the --json-schema judge on an equally heavy round (realityverify-1784109596-81027) ran the full
# 600s and was killed by `timeout` with zero output, showing 600s no longer has enough headroom.
# Raised 900->1200 (2026-07-15, incident realityverify-1784123104-80599): even after the entity-dedup
# fix above cuts redundant navigations, a round with several talkroom-status claims can legitimately
# need ~12-15 real sequential page loads (each ~15-70s, occasionally spiking much higher on real network
# jitter — this incident had one single 181s gap between two ordinary nav calls) plus the 4 mandatory
# ground-truth URLs. auditor.sh runs this hourly (StartCalendarInterval Minute=45), so 1200s (20min)
# still leaves a 40min safety margin before the next scheduled run — there is no cadence conflict.

mkdir -p "$G" "$(dirname "$SELFHEAL")"
echo "$(date '+%F %T') gig_reality_verify: starting (N=$N)" >&2

# ─── 1. Collect the most recent N claim rows from each source (deterministic, no judgment here) ──
CLAIMS_JSON=$("$PY" - "$G" "$N" <<'PYEOF' 2>>"$G/.reality-verify.err.log"
# ENTITY-ID FILTER (FIND-005, reality-verify false-positive round realityverify-1783813501-61933):
# the gig core also appends pass-level bookkeeping/audit rows to these same jsonl files — e.g. B2's
# "zero_applied_exhaustive_scan" summary, whose free-text `note` recaps dozens of ALREADY-PROCESSED
# requestIds from memory (title shorthand, not copy-pasted from the page). These rows assert NO new
# side effect (nothing to verify against a real screen) yet stuffing them into claims_to_verify let
# the judge pick an incidental paraphrase slip inside the prose (a title mixed up between two
# historical requestIds) and fail the WHOLE round over it. The core itself already marks these rows
# deterministically: every genuine entity-specific claim carries a real Coconala requestId/service_id;
# every pass-summary/audit row uses the literal sentinel "N/A" (self-adopted convention, verified
# ~100%-correlated with no-op statuses like zero_applied_exhaustive_scan/reviewed_no_new_action_needed
# across ~300 historical rows). This is structural-field filtering on that existing sentinel, not new
# judgment about prose content — statuses stay 100% free-form (agent's own words, never hardcoded).
import json, os, sys
G, N = sys.argv[1], int(sys.argv[2])
NO_CLAIM_ID = {"", "n/a", "na", "none", "null"}

def tail_rows(fname, kind):
    p = os.path.join(G, fname)
    rows = []
    if not os.path.exists(p):
        return rows
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        entity_id = d.get("requestId") or d.get("service_id") or ""
        if str(entity_id).strip().lower() in NO_CLAIM_ID:
            continue  # pass-level bookkeeping/audit row — no entity-specific side effect to verify
        d["kind"] = kind
        rows.append(d)
    return rows[-N:]

claims = (
    tail_rows("shuppin.jsonl", "shuppin")
    + tail_rows("applied.jsonl", "applied")
    + tail_rows("earnings.jsonl", "earnings")
)

# ENTITY DEDUP (2026-07-15 self-fix, incident realityverify-1784123104-80599 timeout): the gig core
# often self-corrects the SAME entity twice within one N-row tail window (e.g. edits service 4244506's
# title, then a later pass verifies/re-fixes that same title) -- both rows are genuine claims in time,
# but reality-verification only needs to check that entity's CURRENT real-page state ONCE; sending both
# to the judge doubles a real Coconala navigation for zero extra signal. Root-caused from this incident's
# trajectory: 5 shuppin rows collapsed to only 3 distinct service_ids (4244910, 4313386x2, 4244506x2),
# and the judge still burned its full 900s timeout navigating 20 real pages without finishing. Keep only
# the LATEST row per (kind, entity_id) -- deterministic bookkeeping on the same structural id fields
# already used above (requestId/service_id), no judgment about claim content involved.
deduped = {}
for c in claims:
    key = (c.get("kind"), c.get("requestId") or c.get("service_id") or "")
    deduped[key] = c  # later occurrence in claims (== later in file) overwrites -> keeps latest
claims = list(deduped.values())
print(json.dumps(claims, ensure_ascii=False))
PYEOF
)
CLAIMS_RC=$?
if [ "$CLAIMS_RC" -ne 0 ] || [ -z "$CLAIMS_JSON" ]; then
  echo "$(date '+%F %T') gig_reality_verify: claim-collection failed (rc=$CLAIMS_RC), treating as empty" >&2
  CLAIMS_JSON="[]"
fi
CLAIMS_COUNT=$("$PY" -c "import json,sys; print(len(json.loads(sys.argv[1])))" "$CLAIMS_JSON" 2>/dev/null || echo 0)
echo "$(date '+%F %T') gig_reality_verify: collected $CLAIMS_COUNT claim rows" >&2

if [ "$CLAIMS_COUNT" -eq 0 ]; then
  echo "$(date '+%F %T') gig_reality_verify: no claims to verify this round — recording no_claims, not spawning a judge" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':None,'note':'no_claims','claims_checked':0}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  echo "$ROW"
  exit 0
fi

# ─── 2. Stable pass_id + run-start bound, generated BEFORE the spawn (REQ-008, FIND-003) ─────────
# The SAME pass_id is embedded in the prompt and used later by the evidence gate — the judge never
# chooses its own pass_id, so all its navigation-helper captures land under one known directory.
PASS_ID="realityverify-$(date +%s)-$$"
export ANICCA_BUDGET_SCOPE_ID="$PASS_ID"
export ANICCA_PASS_TOKEN_BUDGET="${GIG_AUDIT_TOKEN_BUDGET:-32768}"
export ANICCA_LOOP_DAILY_TOKEN_BUDGET="${GIG_DAILY_TOKEN_BUDGET:-262144}"
# Own daily pool. Sharing the loop's pool meant this 262144 limit was evaluated
# against the revenue pass's millions, so the auditor never got a model call
# after the first pass of the day. Its own peak spend is 86,940/day (07-26).
export ANICCA_BUDGET_DAILY_SCOPE="${GIG_BUDGET_DAILY_SCOPE:-gig-auditor}"
export ANICCA_BUDGET_REQUIRED="${ANICCA_BUDGET_REQUIRED:-1}"
export ANICCA_TOKEN_BUDGET_LEDGER="${GIG_TOKEN_BUDGET_LEDGER:-$HOME/.local/state/anicca/telemetry/token-budget.jsonl}"
RUN_START=$(date +%s)
echo "$(date '+%F %T') gig_reality_verify: pass_id=$PASS_ID run_start=$RUN_START" >&2

# required evidence count = number of ground-truth URLs the judge was told to check this round
# (derived from gig_judge.DEFAULT_GROUND_TRUTH_URLS, never hardcoded blind — REQ-008).
REQUIRED_COUNT=$("$PY" -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('gig_judge', '$SELF_DIR/gig_judge.py')
gig_judge = importlib.util.module_from_spec(spec)
sys.modules['gig_judge'] = gig_judge
spec.loader.exec_module(gig_judge)
print(len(gig_judge.DEFAULT_GROUND_TRUTH_URLS))
" 2>>"$G/.reality-verify.err.log")
if [ -z "$REQUIRED_COUNT" ]; then REQUIRED_COUNT=3; fi

# ─── 3. Build the report-skeptical prompt (PURE — gig_judge.py has no LLM/network call) ──────────
PROMPT=$("$PY" - "$SELF_DIR" "$CLAIMS_JSON" "$PASS_ID" <<'PYEOF' 2>>"$G/.reality-verify.err.log"
import importlib.util, json, os, sys
self_dir, claims_json, pass_id = sys.argv[1], sys.argv[2], sys.argv[3]
spec = importlib.util.spec_from_file_location("gig_judge", os.path.join(self_dir, "gig_judge.py"))
gig_judge = importlib.util.module_from_spec(spec)
sys.modules["gig_judge"] = gig_judge
spec.loader.exec_module(gig_judge)
claims = json.loads(claims_json)
print(gig_judge.build_verifier_prompt(claims, pass_id, gig_judge.DEFAULT_GROUND_TRUTH_URLS))
PYEOF
)
if [ -z "$PROMPT" ]; then
  echo "$(date '+%F %T') gig_reality_verify: prompt build failed" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':False,'failure_reason':'prompt_build_failed','claims_checked':0,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  echo "$ROW"
  exit 1
fi

# ─── 3.5 Dedicated Gig CDP mutex (gig L1-d) — acquire BEFORE browser verification ───────────────
# The verifier and core share one dedicated Gig runtime. Even though read-only verification now
# uses owned hidden targets, serialize it against application/form mutations. Steps 1-3 are
# file-only. If the core holds the lock and does not release within the wait window, DEFER this
# round: record note=deferred_cdp_busy, do NOT spawn, do NOT write a selfheal-request (a deferral is
# not a reality failure). The lock auto-steals a stale holder (crashed core) via cdp_lock.sh.
# Runtime path is anchored to this script's directory.
# shellcheck disable=SC1091
source "$SELF_DIR/scripts/cdp_lock.sh"
if ! cdp_lock_acquire "reality-verifier" 120; then
  echo "$(date '+%F %T') gig_reality_verify: Gig CDP busy (core driving) — deferring this round" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':None,'note':'deferred_cdp_busy','claims_checked':$CLAIMS_COUNT,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  echo "$ROW"
  exit 0
fi
trap 'cdp_lock_release' EXIT

# ─── 3.6 CDP HEALTH GUARD (2026-07-13 fix) — ensure the daily-driver is actually alive before ────
# spawning the judge. cdp_daily_driver_guard.sh already existed (root-caused the starved-accept-queue
# failure mode) but had ZERO callers anywhere in the codebase — the mutex above only arbitrates WHO
# drives the dedicated runtime, it never checks whether the browser process is even up. Root cause of the
# evidence_captured=0/"connection refused" reality_verify_failed rounds (audit-reality.jsonl
# ts=1783896511): the daily-driver Chromium died (WindowServer port death) and nothing ever noticed
# or relaunched it, so every subsequent judge spawn burned its full 600s timeout hitting a dead port.
# We hold the CDP lock at this point (exclusive), so it is safe to kill+relaunch here.
# Runtime path is anchored to this script's directory.
# shellcheck disable=SC1091
source "$SELF_DIR/scripts/cdp_daily_driver_guard.sh"
if ! cdp_guard_ensure_healthy 6 45; then
  echo "$(date '+%F %T') gig_reality_verify: Gig CDP unreachable even after guard relaunch attempt — recording infra failure, not spawning judge" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':False,'failure_reason':'cdp_daily_driver_down_after_guard_relaunch','claims_checked':$CLAIMS_COUNT,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  "$PY" -c "import json,time; print(json.dumps({'reason':'reality_verify_failed','failure_reason':'cdp_daily_driver_down_after_guard_relaunch','ts':int(time.time())}, ensure_ascii=False))" > "$SELFHEAL"
  echo "$ROW"
  exit 0
fi

# ─── 3.7 SESSION RESTORE (2026-07-13, L0-2) — the verifier must be LOGGED IN before it judges ────
# Root cause of the all-day auth_wall FALSE->respawn cycle: the judge navigated Coconala while the
# session had dropped, every ground-truth URL redirected to /login, and a logged-out verifier
# recorded verdict=false — accusing a healthy loop of lying. We hold the CDP lock here (exclusive)
# and the browser is up, so restore the banked login first, then confirm it took.
VAULT="$GIG_BROWSER_DIR/scripts/session_vault.py"
"$PY" "$VAULT" restore >/dev/null 2>&1 || true
KA=$("$PY" "$SELF_DIR/scripts/cdp_nav_snapshot.py" probe-session \
  --url "https://coconala.com/mypage/dashboard" 2>/dev/null || echo '{}')
LOGGED_OUT=$("$PY" -c "import json,sys; print('1' if json.loads(sys.argv[1]).get('logged_out') else '0')" "$KA" 2>/dev/null || echo 0)
if [ "$LOGGED_OUT" = "1" ]; then
  echo "$(date '+%F %T') gig_reality_verify: still logged out after vault restore — DEFER (not a lie)" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':None,'note':'deferred_session_logged_out','claims_checked':$CLAIMS_COUNT,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  echo "$ROW"
  exit 0
fi

# ─── 4. Spawn a fresh, report-independent judge through the common runner ───────────────────────
# The judge calls cdp_nav_snapshot.py against the dedicated Gig CDP runtime without interactive input.
# Provider/model/effort remain in runner config. The prompt instructs the judge to use the
# deterministic nav helper with
# PASS_ID for every ground-truth URL — enforced independently by step 5's evidence gate, not trusted.
#
# --json-schema (2026-07-15 fix, incident realityverify-1784108700-56675): previously ran with plain
# --output-format text and gig_reality_gate.py regex-scraped the final JSON object out of free text.
# On a heavy round (10 claims, 4 ground-truth URLs, long report-skeptical instructions) the judge
# sometimes finished its investigation but never emitted the final JSON block at all (pure prose
# response, zero "{"/"}" anywhere) — gig_reality_gate.py then raised "no JSON object found in judge
# output" and the round was recorded verdict=false/kind=claim_mismatch even though the trajectory
# showed all 4 URLs were navigated successfully while logged in (real evidence existed; nothing was
# actually wrong with the gig core's claims, the judge itself just failed to follow the
# response-format instruction under load). This is the same class of bug the trajectory_all_login_wall
# backstop in gig_reality_gate.py already patched for the auth-wall case, but that backstop only fires
# when every navigated URL was a /login redirect — a non-auth-wall unparseable response fell through
# it. --json-schema makes the CLI itself enforce structured output on the judge's FINAL answer
# (verified live: interim Bash/browser tool calls still run normally, only the concluding response is
# schema-shaped) — this removes the failure mode at the source instead of catching it after the fact.
mkdir -p "$TRAJECTORY_ROOT/$PASS_ID"
JUDGE_PROMPT_FILE="$TRAJECTORY_ROOT/$PASS_ID/judge.prompt.txt"
RUNNER_EVIDENCE="$TRAJECTORY_ROOT/$PASS_ID/agent-runner"
printf '%s' "$PROMPT" > "$JUDGE_PROMPT_FILE"
echo "$(date '+%F %T') gig_reality_verify: spawning bounded tool-agent judge through common runner" >&2
RUNNER_SUMMARY=$(python3 "$RUNNER" --task-class tool-agent --prompt-file "$JUDGE_PROMPT_FILE" \
  --schema "$JUDGE_SCHEMA_FILE" --evidence-dir "$RUNNER_EVIDENCE" \
  --task-label gig-reality-judge --loop gig --workdir "$HOME" < /dev/null 2>>"$G/.reality-verify.err.log")
JUDGE_RC=$?
if [ "$JUDGE_RC" -eq 75 ]; then
  BUDGET_REASON=$(printf '%s' "$RUNNER_SUMMARY" | "$PY" -c \
    'import json,sys; print((json.load(sys.stdin).get("budget") or {}).get("reason") or "token_budget_exceeded")' \
    2>/dev/null || echo token_budget_exceeded)
  echo "$(date '+%F %T') gig_reality_verify: judge skipped by token circuit breaker ($BUDGET_REASON)" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':None,'note':'budget_blocked','failure_reason':'$BUDGET_REASON','claims_checked':$CLAIMS_COUNT,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  echo "$ROW"
  exit 0
fi
RESULT_PATH=$(printf '%s' "$RUNNER_SUMMARY" | "$PY" -c 'import json,sys; print(json.load(sys.stdin).get("result_path") or "")' 2>/dev/null || true)
if [ -n "$RESULT_PATH" ] && [ -f "$RESULT_PATH" ]; then
  JUDGE_RAW=$(cat "$RESULT_PATH")
else
  JUDGE_RAW=""
  if [ -f "$RUNNER_EVIDENCE/attempts.jsonl" ] && tail -1 "$RUNNER_EVIDENCE/attempts.jsonl" | "$PY" -c 'import json,sys; raise SystemExit(0 if json.load(sys.stdin).get("timed_out") else 1)' 2>/dev/null; then
    JUDGE_RC=124
  fi
fi
# always persist the raw judge response for post-mortem — previously nothing was kept when parsing
# failed, which is why this incident had to be root-caused blind (no raw text survived).
printf '%s' "$JUDGE_RAW" > "$TRAJECTORY_ROOT/$PASS_ID/judge_raw.txt" 2>/dev/null || true

if [ "$JUDGE_RC" -eq 124 ]; then
  echo "$(date '+%F %T') gig_reality_verify: fresh judge TIMED OUT after ${TIMEOUT_SECS}s" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':False,'failure_reason':'timeout','claims_checked':$CLAIMS_COUNT,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  "$PY" -c "import json,time; print(json.dumps({'reason':'reality_verify_timeout','kind':'timeout','failure_reason':'fresh judge spawn timed out','ts':int(time.time())}, ensure_ascii=False))" > "$SELFHEAL"
  echo "$ROW"
  exit 0
fi

# ─── 4.5 ABNORMAL-EXIT GUARD (2026-07-19 self-fix, incident realityverify-1784457900-26730 /
# -1784461504-62154 / -1784465105-99788): three consecutive rounds recorded verdict=false with
# failure_reason "unparseable_judge_output: no JSON object found in judge output" AND an empty
# ($TRAJECTORY_ROOT/$PASS_ID/judge_raw.txt = 0 bytes) judge response in only 19-45s -- far too fast
# for the judge to have actually navigated the 4 ground-truth URLs (legitimate rounds take 400-900s+,
# see the TIMEOUT_SECS history above). Root-caused live: `vm_stat`/`sysctl vm.swapusage` at incident
# time showed ~67MB free RAM and 727MB free swap (23.8/24.5GB swap used, disk at 2.7GB free) with 89
# concurrent agent processes already running on this host -- a manual reproduction of the exact
# same spawn was jetsam SIGKILLed (rc=137) by macOS before emitting any
# output. This is host memory/resource exhaustion, NOT the judge disagreeing with the gig core's
# claims -- gig_reality_gate.py has no way to tell "judge never ran" apart from "judge ran and
# refused to follow the JSON-schema instruction", so it was mis-classifying starvation as
# kind=claim_mismatch and unconditionally spawning another self-fix agent every hour, deepening
# the resource exhaustion it gets blamed for.
# Detect it deterministically here (before the gate ever sees it) via the same signal used above for
# timeout: JUDGE_RC nonzero-and-not-124 (128+signal for a kill, e.g. 137=SIGKILL/139=SIGSEGV) combined
# with a genuinely empty judge_raw.txt -- both true only when the process never got to run, not when
# it ran and produced bad prose (that case still has RC=0 and falls through to the real gate below).
JUDGE_RAW_BYTES=$(wc -c < "$TRAJECTORY_ROOT/$PASS_ID/judge_raw.txt" 2>/dev/null | tr -d ' ')
if [ "$JUDGE_RC" -ne 0 ] && [ "${JUDGE_RAW_BYTES:-0}" -eq 0 ]; then
  echo "$(date '+%F %T') gig_reality_verify: fresh judge exited abnormally (rc=$JUDGE_RC, zero-byte output) -- treating as host resource exhaustion, NOT a claim/reality mismatch" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':False,'failure_reason':'judge_process_killed_rc$JUDGE_RC','claims_checked':$CLAIMS_COUNT,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  "$PY" -c "import json,time; print(json.dumps({'reason':'reality_verify_failed','kind':'judge_process_killed','failure_reason':'fresh judge process exited abnormally (rc=$JUDGE_RC) with zero output -- likely host memory/swap exhaustion (see vm_stat/vm.swapusage), not a code bug','ts':int(time.time())}, ensure_ascii=False))" > "$SELFHEAL"
  echo "$ROW"
  exit 0
fi

# ─── 5. Deterministic evidence gate (REQ-007, FIND-002 fix) — NEVER accept verdict on faith alone ─
# gig_reality_gate.py parses the judge's JSON, then counts the REAL trajectory rows this pass_id
# captured (ts >= RUN_START) and applies gig_judge.gate_verdict: an unbacked verdict:true (fewer
# fresh evidence rows than ground-truth URLs) is downgraded to false. This is pure bash/python over the
# real trajectory file — no LLM is asked to grade itself a second time.
PARSED_ROW=$("$PY" "$SELF_DIR/scripts/gig_reality_gate.py" "$JUDGE_RAW" "$PASS_ID" "$REQUIRED_COUNT" "$RUN_START" "$TRAJECTORY_ROOT" "$CLAIMS_COUNT" 2>>"$G/.reality-verify.err.log")
if [ -z "$PARSED_ROW" ]; then
  PARSED_ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':False,'failure_reason':'unparseable_judge_output: empty_gate_output','claims_checked':$CLAIMS_COUNT,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
fi

echo "$PARSED_ROW" >> "$AUDIT_REALITY"
echo "$(date '+%F %T') gig_reality_verify: recorded gated verdict row" >&2

# ─── 6. On verdict:false → write selfheal-request; on verdict:true → do NOT touch it ─────────────
IS_FALSE=$("$PY" -c "import json,sys; d=json.loads(sys.argv[1]); print('1' if d.get('verdict') is False else '0')" "$PARSED_ROW" 2>/dev/null || echo 0)
if [ "$IS_FALSE" = "1" ]; then
  "$PY" -c "
import json, sys, time
d = json.loads(sys.argv[1])
# kind classification (2026-07-13 self-fix, gh#1015): reached_captcha=true means the judge could NOT
# even reach the real ground-truth screens (login/auth wall) -- there is no claim-vs-reality mismatch
# for code to fix, it's an external/session precondition. Only a false verdict WITHOUT reached_captcha
# is a genuine claim_mismatch (the judge DID see the real screen and the core's claim did not hold
# there) -- that is the case worth an unconditional self-fix.sh code-bug spawn. auditor.sh reads this
# 'kind' to cooldown-gate auth_wall spawns instead of respawning a full agent every hourly audit pass.
kind = 'auth_wall' if d.get('reached_captcha') else 'claim_mismatch'
out = {'reason': 'reality_verify_failed', 'kind': kind, 'failure_reason': d.get('failure_reason'), 'ts': int(time.time())}
print(json.dumps(out, ensure_ascii=False))
" "$PARSED_ROW" > "$SELFHEAL"
  echo "$(date '+%F %T') gig_reality_verify: verdict=false -> wrote selfheal-request" >&2
fi

echo "$PARSED_ROW"
