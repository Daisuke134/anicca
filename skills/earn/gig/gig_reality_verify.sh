#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"  # claude lives in ~/.local/bin (npm global), matching self-fix.sh
# gig_reality_verify.sh — the reality-verifier runner for the gig loop (feature gig-reality-verify,
# 増分2b: docs/loop-engineering/26-gig-loop-asis-tobe-plan.md §8, BP §2/§7 of
# docs/loop-engineering/25-browser-use-verify-selfimprove-bp.md). Called by auditor.sh AFTER its
# existing deterministic verdict, so the gig loop is judged not just by "did files change" but by
# "does the REAL Coconala screen match what the core claimed" — a FRESH, report-independent
# `claude -p` spawn (no memory of the gig core's session) does the actual judging via gig_judge.py's
# report-skeptical prompt, navigating :9222 (via the DETERMINISTIC cdp_nav_snapshot.py helper —
# behavioral-spec REQ-006) and reading the real DOM/screenshots itself.
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

G="$HOME/gig"
AUDIT_REALITY="$G/audit-reality.jsonl"
SELFHEAL="$HOME/.openclaw/state/.gig-core-selfheal-request.json"
PY="$(command -v python3 || echo /opt/homebrew/bin/python3)"
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="$HOME/profitable-claude/skills/agent-runner/agent_runner.py"
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

# ─── 1. Collect each new claim once (deterministic, evidence-backed watermark) ──────────────
# A last-N-only window re-submitted an already-judged listing claim forever when Coconala later
# returned that listing to draft. The collector now advances only past claims from a round that
# captured all required real-page evidence; CDP failures, timeouts, and deferrals remain retryable.
CLAIMS_ENVELOPE=$("$PY" "$SELF_DIR/scripts/gig_reality_claims.py" "$G" "$N" 2>>"$G/.reality-verify.err.log")
CLAIMS_RC=$?
if [ "$CLAIMS_RC" -ne 0 ] || [ -z "$CLAIMS_ENVELOPE" ]; then
  echo "$(date '+%F %T') gig_reality_verify: claim-collection failed (rc=$CLAIMS_RC), treating as empty" >&2
  CLAIMS_ENVELOPE='{"claims":[],"watermark":0,"claims_through_ts":0}'
fi
CLAIMS_JSON=$("$PY" -c "import json,sys; print(json.dumps(json.loads(sys.argv[1]).get('claims', []), ensure_ascii=False))" "$CLAIMS_ENVELOPE" 2>/dev/null || echo '[]')
CLAIMS_THROUGH_TS=$("$PY" -c "import json,sys; print(json.loads(sys.argv[1]).get('claims_through_ts', 0))" "$CLAIMS_ENVELOPE" 2>/dev/null || echo 0)
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

# ─── 3.5 CDP :9222 mutex (gig L1-d) — acquire BEFORE the browser-driving judge spawn so the ────
# verifier never navigates the shared daily-driver tab while the core's :27 pass is mid-応募/フォーム
# 入力 (and vice versa). Steps 1-3 above are file-only (no browser); the judge spawn below is what
# drives :9222. If the core holds the lock and does not release within the wait window, DEFER this
# round: record note=deferred_cdp_busy, do NOT spawn, do NOT write a selfheal-request (a deferral is
# not a reality failure). The lock auto-steals a stale holder (crashed core) via cdp_lock.sh.
source "$SELF_DIR/scripts/cdp_lock.sh"
if ! cdp_lock_acquire "reality-verifier" 120; then
  echo "$(date '+%F %T') gig_reality_verify: :9222 busy (core driving) — deferring this round" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':None,'note':'deferred_cdp_busy','claims_checked':$CLAIMS_COUNT,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  echo "$ROW"
  exit 0
fi
trap 'cdp_lock_release' EXIT

# ─── 3.6 CDP HEALTH GUARD (2026-07-13 fix) — ensure the daily-driver is actually alive before ────
# spawning the judge. cdp_daily_driver_guard.sh already existed (root-caused the starved-accept-queue
# failure mode) but had ZERO callers anywhere in the codebase — the mutex above only arbitrates WHO
# drives :9222, it never checks whether the browser process is even up. Root cause of the
# evidence_captured=0/"connection refused" reality_verify_failed rounds (audit-reality.jsonl
# ts=1783896511): the daily-driver Chromium died (WindowServer port death) and nothing ever noticed
# or relaunched it, so every subsequent judge spawn burned its full 600s timeout hitting a dead port.
# We hold the CDP lock at this point (exclusive), so it is safe to kill+relaunch here.
source "$SELF_DIR/scripts/cdp_daily_driver_guard.sh"
if ! cdp_guard_ensure_healthy 6 45; then
  echo "$(date '+%F %T') gig_reality_verify: CDP :9222 unreachable even after guard relaunch attempt — recording infra failure, not spawning judge" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':False,'failure_reason':'cdp_daily_driver_down_after_guard_relaunch','claims_checked':$CLAIMS_COUNT,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  "$PY" -c "import json,time; print(json.dumps({'reason':'reality_verify_failed','kind':'infra','failure_reason':'cdp_daily_driver_down_after_guard_relaunch','ts':int(time.time())}, ensure_ascii=False))" > "$SELFHEAL"
  echo "$ROW"
  exit 0
fi

# ─── 3.7 SESSION RESTORE (2026-07-13, L0-2) — the verifier must be LOGGED IN before it judges ────
# Root cause of the all-day auth_wall FALSE->respawn cycle: the judge navigated Coconala while the
# session had dropped, every ground-truth URL redirected to /login, and a logged-out verifier
# recorded verdict=false — accusing a healthy loop of lying. We hold the CDP lock here (exclusive)
# and the browser is up, so restore the banked login first, then confirm it took.
VAULT="$HOME/anicca/skills/browser/scripts/session_vault.py"
"$PY" "$VAULT" restore >/dev/null 2>&1 || true
KA=$("$PY" "$VAULT" keepalive "https://coconala.com/mypage/dashboard" 2>/dev/null || echo '{}')
LOGGED_OUT=$("$PY" -c "import json,sys; print('1' if json.loads(sys.argv[1]).get('logged_out') else '0')" "$KA" 2>/dev/null || echo 0)
if [ "$LOGGED_OUT" = "1" ]; then
  echo "$(date '+%F %T') gig_reality_verify: still logged out after vault restore — DEFER (not a lie)" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':None,'note':'deferred_session_logged_out','claims_checked':$CLAIMS_COUNT,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  echo "$ROW"
  exit 0
fi

# ─── 4. Spawn a fresh, report-independent judge through the common runner ──────────────
# Reuse the deployed runner's provider fallback instead of pinning one Claude credential pool. The
# runner keeps provider/model policy outside this loop and persists every attempt for diagnosis.
mkdir -p "$TRAJECTORY_ROOT/$PASS_ID"
JUDGE_PROMPT_FILE="$TRAJECTORY_ROOT/$PASS_ID/judge.prompt.txt"
RUNNER_EVIDENCE="$TRAJECTORY_ROOT/$PASS_ID/agent-runner"
printf '%s' "$PROMPT" > "$JUDGE_PROMPT_FILE"
echo "$(date '+%F %T') gig_reality_verify: spawning fresh high-value-agent judge through common runner" >&2
RUNNER_SUMMARY=$("$PY" "$RUNNER" --task-class high-value-agent --prompt-file "$JUDGE_PROMPT_FILE" \
  --schema "$JUDGE_SCHEMA_FILE" --evidence-dir "$RUNNER_EVIDENCE" \
  --task-label gig-reality-judge --workdir "$HOME" < /dev/null 2>>"$G/.reality-verify.err.log")
JUDGE_RC=$?
RESULT_PATH=$(printf '%s' "$RUNNER_SUMMARY" | "$PY" -c 'import json,sys; print(json.load(sys.stdin).get("result_path") or "")' 2>/dev/null || true)
if [ -n "$RESULT_PATH" ] && [ -f "$RESULT_PATH" ]; then
  JUDGE_RAW=$(cat "$RESULT_PATH")
else
  JUDGE_RAW=""
  if [ -f "$RUNNER_EVIDENCE/attempts.jsonl" ] && tail -1 "$RUNNER_EVIDENCE/attempts.jsonl" | "$PY" -c 'import json,sys; raise SystemExit(0 if json.load(sys.stdin).get("timed_out") else 1)' 2>/dev/null; then
    JUDGE_RC=124
  fi
fi
printf '%s' "$JUDGE_RAW" > "$TRAJECTORY_ROOT/$PASS_ID/judge_raw.txt" 2>/dev/null || true

if [ "$JUDGE_RC" -eq 124 ]; then
  echo "$(date '+%F %T') gig_reality_verify: fresh judge TIMED OUT after ${TIMEOUT_SECS}s" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':False,'failure_reason':'timeout','claims_checked':$CLAIMS_COUNT,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  "$PY" -c "import json,time; print(json.dumps({'reason':'reality_verify_timeout','kind':'timeout','failure_reason':'fresh judge spawn timed out','ts':int(time.time())}, ensure_ascii=False))" > "$SELFHEAL"
  echo "$ROW"
  exit 0
fi

JUDGE_RAW_BYTES=$(wc -c < "$TRAJECTORY_ROOT/$PASS_ID/judge_raw.txt" 2>/dev/null | tr -d ' ')
if [ "$JUDGE_RC" -ne 0 ] && [ "${JUDGE_RAW_BYTES:-0}" -eq 0 ]; then
  echo "$(date '+%F %T') gig_reality_verify: fresh judge exited abnormally (rc=$JUDGE_RC, zero-byte output) -- infra failure, not claim mismatch" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':False,'failure_reason':'judge_process_failed_rc$JUDGE_RC','claims_checked':$CLAIMS_COUNT,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  "$PY" -c "import json,time; print(json.dumps({'reason':'reality_verify_failed','kind':'judge_process_failed','failure_reason':'fresh judge failed before producing output (rc=$JUDGE_RC)','ts':int(time.time())}, ensure_ascii=False))" > "$SELFHEAL"
  echo "$ROW"
  exit 0
fi

# ─── 5. Deterministic evidence gate (REQ-007, FIND-002 fix) — NEVER accept verdict on faith alone ─
# gig_reality_gate.py parses the judge's JSON, then counts the REAL trajectory rows this pass_id
# captured (ts >= RUN_START) and applies gig_judge.gate_verdict: an unbacked verdict:true (fewer
# fresh screenshots than ground-truth URLs) is downgraded to false. This is pure bash/python over the
# real trajectory file — no LLM is asked to grade itself a second time.
PARSED_ROW=$("$PY" "$SELF_DIR/scripts/gig_reality_gate.py" "$JUDGE_RAW" "$PASS_ID" "$REQUIRED_COUNT" "$RUN_START" "$TRAJECTORY_ROOT" "$CLAIMS_COUNT" 2>>"$G/.reality-verify.err.log")
if [ -z "$PARSED_ROW" ]; then
  PARSED_ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':False,'failure_reason':'unparseable_judge_output: empty_gate_output','claims_checked':$CLAIMS_COUNT,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
fi

# Mark claims consumed only after the deterministic gate confirms that every required real-page
# capture exists. A true or false claim judgement is final input to the self-heal loop; infra-only
# failures with incomplete evidence intentionally leave the claim pending for a later retry.
PARSED_ROW=$("$PY" -c "
import json,sys
d=json.loads(sys.argv[1]); through=float(sys.argv[2]); required=int(d.get('evidence_required') or 0); captured=int(d.get('evidence_captured') or 0)
if required > 0 and captured >= required: d['claims_through_ts']=through
print(json.dumps(d, ensure_ascii=False))
" "$PARSED_ROW" "$CLAIMS_THROUGH_TS")

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
