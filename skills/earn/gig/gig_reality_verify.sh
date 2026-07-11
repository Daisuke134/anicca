#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"  # claude lives in ~/.local/bin (npm global), matching self-fix.sh
# gig_reality_verify.sh — the reality-verifier runner for the gig loop (feature gig-reality-verify,
# 増分2b: docs/loop-engineering/26-gig-loop-asis-tobe-plan.md §8, BP §2/§7 of
# docs/loop-engineering/25-browser-use-verify-selfimprove-bp.md). Called by auditor.sh AFTER its
# existing deterministic verdict, so the gig loop is judged not just by "did files change" but by
# "does the REAL Coconala screen match what the core claimed" — a FRESH, report-independent
# `claude -p` spawn (no memory of the gig core's session) does the actual judging via gig_judge.py's
# report-skeptical prompt, navigating :9222 and reading the real DOM/screenshots itself.
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

# ─── 2. Build the report-skeptical prompt (PURE — gig_judge.py has no LLM/network call) ──────────
PROMPT=$("$PY" - "$SELF_DIR" "$CLAIMS_JSON" <<'PYEOF' 2>>"$G/.reality-verify.err.log"
import importlib.util, json, os, sys
self_dir, claims_json = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("gig_judge", os.path.join(self_dir, "gig_judge.py"))
gig_judge = importlib.util.module_from_spec(spec)
sys.modules["gig_judge"] = gig_judge
spec.loader.exec_module(gig_judge)
claims = json.loads(claims_json)
print(gig_judge.build_verifier_prompt(claims, gig_judge.DEFAULT_GROUND_TRUTH_URLS))
PYEOF
)
if [ -z "$PROMPT" ]; then
  echo "$(date '+%F %T') gig_reality_verify: prompt build failed" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':False,'failure_reason':'prompt_build_failed','claims_checked':0}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  echo "$ROW"
  exit 1
fi

# ─── 3. Spawn a FRESH, report-independent claude -p judge (subscription session, capped) ─────────
# env -u ANTHROPIC_API_KEY: use the Claude subscription login (parity: gig-cli.sh/self-fix.sh spawn
# idiom), not pay-per-token API billing. --dangerously-skip-permissions + --add-dir "$HOME": the
# judge must freely drive CDP :9222 (browser) and call cdp_snapshot.py under $HOME without prompts —
# this is a non-interactive, autonomous fresh spawn (adversary-daily.sh `claude -p` idiom, adapted).
echo "$(date '+%F %T') gig_reality_verify: spawning fresh claude -p judge (timeout ${TIMEOUT_SECS}s)" >&2
JUDGE_RAW=$(env -u ANTHROPIC_API_KEY timeout "$TIMEOUT_SECS" \
  "$CLAUDE" -p "$PROMPT" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" --output-format text \
  2>>"$G/.reality-verify.err.log")
JUDGE_RC=$?

if [ "$JUDGE_RC" -eq 124 ]; then
  echo "$(date '+%F %T') gig_reality_verify: fresh judge TIMED OUT after ${TIMEOUT_SECS}s" >&2
  ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':False,'failure_reason':'timeout','claims_checked':$CLAIMS_COUNT}, ensure_ascii=False))")
  echo "$ROW" >> "$AUDIT_REALITY"
  "$PY" -c "import json,time; print(json.dumps({'reason':'reality_verify_timeout','failure_reason':'fresh judge spawn timed out','ts':int(time.time())}, ensure_ascii=False))" > "$SELFHEAL"
  echo "$ROW"
  exit 0
fi

# ─── 4. Parse the judge's JSON verdict (never trust unparseable output — record + selfheal) ──────
PARSED_ROW=$("$PY" - "$SELF_DIR" "$JUDGE_RAW" "$CLAIMS_COUNT" <<'PYEOF' 2>>"$G/.reality-verify.err.log"
import importlib.util, json, os, re, sys, time
self_dir, raw, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
spec = importlib.util.spec_from_file_location("gig_judge", os.path.join(self_dir, "gig_judge.py"))
gig_judge = importlib.util.module_from_spec(spec)
sys.modules["gig_judge"] = gig_judge
spec.loader.exec_module(gig_judge)

def extract_json_obj(text):
    # the judge is instructed to print ONLY the JSON object; tolerate stray whitespace/fencing.
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("no JSON object found in judge output")
    return json.loads(m.group(0))

try:
    d = extract_json_obj(raw)
    jr = gig_judge.JudgementResult.from_dict(d)
    row = {
        "ts": int(time.time()), "verdict": jr.verdict, "reasoning": jr.reasoning,
        "failure_reason": jr.failure_reason, "impossible_task": jr.impossible_task,
        "reached_captcha": jr.reached_captcha, "claims_checked": n,
    }
except Exception as e:
    row = {
        "ts": int(time.time()), "verdict": False,
        "failure_reason": f"unparseable_judge_output: {e}", "claims_checked": n,
    }
print(json.dumps(row, ensure_ascii=False))
PYEOF
)
if [ -z "$PARSED_ROW" ]; then
  PARSED_ROW=$("$PY" -c "import json,time; print(json.dumps({'ts':int(time.time()),'verdict':False,'failure_reason':'unparseable_judge_output: empty_parse','claims_checked':$CLAIMS_COUNT}, ensure_ascii=False))")
fi

echo "$PARSED_ROW" >> "$AUDIT_REALITY"
echo "$(date '+%F %T') gig_reality_verify: recorded verdict row" >&2

# ─── 5. On verdict:false → write selfheal-request; on verdict:true → do NOT touch it ─────────────
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
