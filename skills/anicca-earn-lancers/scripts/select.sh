#!/usr/bin/env bash
# select.sh — score candidate JIDs and emit top 3.
# stdin: newline-separated JIDs
# stdout: JSON array of 3 scored candidate objects, sorted desc by score.
#
# Scoring source of truth:
#   When --offline-fixture is given, the fixture snapshot is reparsed for
#   (title, budget_jpy) per JID (no Camofox, no LLM — pure deterministic
#   scoring = budget_jpy / effort_estimate). This is what the E2E test pins.
#
#   When live, each JID is fetched via Camofox detail page, parsed for
#   the budget block, and passed to `hermes chat -q --model <mini>` which
#   returns a JSON line with effort_estimate ∈ 1..10. Mini model only
#   (CLAUDE.md HARD RULE: gpt-5.2-mini / deepseek-v4-flash / kimi-k2.6).

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

FIXTURE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --offline-fixture) FIXTURE="$2"; shift 2 ;;
    *) shift ;;
  esac
done

JIDS=$(cat)

if [ -n "$FIXTURE" ]; then
  # Deterministic: parse (jid, title, budget) tuples from the fixture and rank.
  JIDS="$JIDS" "$PYTHON" - "$FIXTURE" <<'PY'
import json, re, os, sys
fixture_path = sys.argv[1]
jids = [j.strip() for j in os.environ.get('JIDS', '').splitlines() if j.strip()]
snap = json.load(open(fixture_path)).get('snapshot', '')
# Each fixture line is: "ref=eN [link] <TITLE> /work/detail/<JID> — 予算 ¥<N>[,<N>]*"
rows = {}
for line in snap.split('\n'):
    m = re.search(r'/work/detail/(\d+)', line)
    if not m: continue
    jid = m.group(1)
    title = re.sub(r'ref=\S+\s+\[link\]\s+', '', line).split('/work/detail/')[0].strip()
    b = re.search(r'予算\s*¥([\d,]+)', line)
    budget = int(b.group(1).replace(',', '')) if b else 0
    rows[jid] = (title, budget)

# effort_estimate proxy from title length + presence of "大規模"/"一括"/"100本"
def effort(title):
    e = 1
    if any(t in title for t in ['大規模','一括','100本','大量']): e += 5
    if len(title) > 20: e += 2
    return max(1, min(10, e))

scored = []
for jid in jids:
    if jid not in rows: continue
    title, budget = rows[jid]
    eff = effort(title)
    score = budget / max(1, eff)
    scored.append({
        "jid": jid,
        "url": f"https://www.lancers.jp/work/detail/{jid}",
        "title_truncated": title[:40],
        "budget_jpy": budget,
        "effort_estimate": eff,
        "score": round(score, 2),
    })

scored.sort(key=lambda r: r['score'], reverse=True)
print(json.dumps(scored[:3], ensure_ascii=False))
PY
  exit 0
fi

# ── LIVE branch ───────────────────────────────────────────────────────────
cf_health || { err "camofox down"; exit 3; }

# Pick the mini model from env or default. HARD RULE: mini only.
MODEL="${LANCERS_SCORE_MODEL:-gpt-5.2-mini}"

ROWS_JSON='[]'
for JID in $JIDS; do
  TAB=$(cf_open "https://www.lancers.jp/work/detail/$JID")
  sleep 4
  SNAP=$(cf_snapshot "$TAB")
  cf_close "$TAB"

  PARSED=$(JID="$JID" SNAP="$SNAP" "$PYTHON" - <<'PY'
import json, re, os
d = json.loads(os.environ.get('SNAP', '{}') or '{}')
snap = d.get('snapshot', '')
jid = os.environ['JID']
title = (re.search(r'(?m)^\s*(?:[#=]+\s*)?(.{4,60})$', snap) or [None, ''])[1].strip() if re.search(r'(?m)^\s*(?:[#=]+\s*)?(.{4,60})$', snap) else ''
b = re.search(r'予算\s*¥?([\d,]+)\s*[-〜~]?\s*¥?([\d,]+)?', snap)
budget = 0
if b:
    budget = int((b.group(2) or b.group(1)).replace(',', ''))
print(json.dumps({"jid": jid, "url": f"https://www.lancers.jp/work/detail/{jid}", "title": title, "budget_jpy": budget}, ensure_ascii=False))
PY
)

  # Ask the mini model for effort 1..10 (single JSON line)
  PROMPT="Read the Lancers gig title and budget. Reply with ONE JSON line only: {\"effort_estimate\": <int 1..10>} where 1=trivial, 10=large multi-week. No prose. Input: $PARSED"
  EFF_LINE=$(hermes chat --model "$MODEL" -q "$PROMPT" 2>/dev/null || echo '{"effort_estimate":5}')
  EFF=$(printf '%s' "$EFF_LINE" | "$JQ" -r '.effort_estimate // 5' 2>/dev/null || echo 5)

  ROW=$("$JQ" -n --argjson p "$PARSED" --argjson e "$EFF" \
    '$p + {effort_estimate:$e, score: ((.budget_jpy // 0) / ([1, $e] | max))}')
  ROWS_JSON=$("$JQ" -n --argjson a "$ROWS_JSON" --argjson r "$ROW" '$a + [$r]')
done

# Sort desc by score, take top 3, add title_truncated + placeholder generated_message
echo "$ROWS_JSON" | "$JQ" '
  sort_by(-.score)
  | .[0:3]
  | map(. + {title_truncated: (.title // "")[0:40], generated_message: ""})
'
