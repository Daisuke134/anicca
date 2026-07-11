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
import json, os, sys
G, N = sys.argv[1], int(sys.argv[2])

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
out = {'reason': 'reality_verify_failed', 'failure_reason': d.get('failure_reason'), 'ts': int(time.time())}
print(json.dumps(out, ensure_ascii=False))
" "$PARSED_ROW" > "$SELFHEAL"
  echo "$(date '+%F %T') gig_reality_verify: verdict=false -> wrote selfheal-request" >&2
fi

echo "$PARSED_ROW"
