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
CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAJECTORY_ROOT="$G/trajectory"
N="${1:-5}"
TIMEOUT_SECS=600   # cap the fresh judge spawn — never block auditor.sh forever (behavioral-spec REQ-004 edge case)

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
  "$PY" -c "import json,time; print(json.dumps({'reason':'reality_verify_failed','failure_reason':'cdp_daily_driver_down_after_guard_relaunch','ts':int(time.time())}, ensure_ascii=False))" > "$SELFHEAL"
  echo "$ROW"
  exit 0
fi

# ─── 4. Spawn a FRESH, report-independent claude -p judge (subscription session, capped) ─────────
# env -u ANTHROPIC_API_KEY: use the Claude subscription login (parity: gig-cli.sh/self-fix.sh spawn
# idiom), not pay-per-token API billing. --dangerously-skip-permissions + --add-dir "$HOME": the
# judge must freely drive CDP :9222 (browser) and call cdp_nav_snapshot.py under $HOME without
# prompts — this is a non-interactive, autonomous fresh spawn (adversary-daily.sh `claude -p` idiom,
# adapted). The judge is instructed (gig_judge prompt) to use the DETERMINISTIC nav helper with
# PASS_ID for every ground-truth URL — enforced independently by step 5's evidence gate, not trusted.
echo "$(date '+%F %T') gig_reality_verify: spawning fresh claude -p judge (timeout ${TIMEOUT_SECS}s)" >&2
JUDGE_RAW=$(env -u ANTHROPIC_API_KEY timeout "$TIMEOUT_SECS" \
  "$CLAUDE" -p "$PROMPT" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" --output-format text \
  2>>"$G/.reality-verify.err.log")
JUDGE_RC=$?

if [ "$JUDGE_RC" -eq 124 ]; then
  echo "$(date '+%F %T') gig_reality_verify: fresh judge TIMED OUT after ${TIMEOUT_SECS}s" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':False,'failure_reason':'timeout','claims_checked':$CLAIMS_COUNT,'pass_id':'$PASS_ID'}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  "$PY" -c "import json,time; print(json.dumps({'reason':'reality_verify_timeout','failure_reason':'fresh judge spawn timed out','ts':int(time.time())}, ensure_ascii=False))" > "$SELFHEAL"
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
