#!/usr/bin/env bash
# gen-script.sh [en] — generate a FRESH faceless personal-finance voiceover script EVERY run,
# copying the PROVEN viral template (head-to-head) from @breakyourbudget (3M views) but with
# brand-new content. NOT a rotation/bank: the LLM writes a new angle each time, and a dedup
# ledger bans recently-used topics so it never repeats → new content every day, forever.
#
# The TEMPLATE is the structural RULE (right-altitude guidance); the CONTENT is the LLM's to
# generate. Outputs JSON {"id","topic","query","script"} to stdout. $0 (DeepSeek pennies).
set -euo pipefail
LANG_CODE="${1:-en}"
set -a; . "$HOME/.openclaw/.env" 2>/dev/null || true; set +a
SK="$HOME/.claude/skills/faceless-money-factory"
ID="money-$(date +%Y%m%d-%H%M%S)"
LEDGER="$SK/state/script-ledger.jsonl"; mkdir -p "$(dirname "$LEDGER")"; touch "$LEDGER"

# recent topics (last 30) so we never repeat → fresh daily
RECENT="$(tail -30 "$LEDGER" 2>/dev/null | python3 -c "import sys,json
t=[]
for l in sys.stdin:
    l=l.strip()
    if not l: continue
    try: t.append(json.loads(l).get('topic',''))
    except: pass
print(' | '.join(x for x in t if x))" 2>/dev/null || echo "")"

SYS="You write faceless personal-finance TikTok/Reels voiceover scripts that copy a PROVEN viral template head-to-head, with brand-new content every time."
read -r -d '' USERP <<EOF || true
Write ONE fresh faceless money script. COPY this winning template EXACTLY (it got 3,000,000 views), only the content is new:
TEMPLATE:
- HOOK (1 sentence): "These are the exact <X> that helped me <impressive SPECIFIC numeric result>. Let's go."
- BODY: a numbered list (First... / Next... / The third... / And the last...). Each item = ONE concrete money concept + ONE actionable numeric rule (a % or \$ figure).
- CTA (last line): "Follow for more money tips."
RULES: strong specific hook with a number; 4 list items; ~110-150 words; natural spoken voiceover; NO emojis; NO hashtags; output ONLY the spoken script text.
Pick a FRESH personal-finance angle (budgeting, saving, investing, debt payoff, credit score, side income, taxes, retirement, no-spend, automation, etc.).
Do NOT reuse any of these recent topics: [${RECENT}]
Also output the topic as a short label on the FIRST line prefixed "TOPIC:" then the script after a blank line.
EOF

# MODEL-AGNOSTIC: the running agent's OWN model writes the script (env decides the provider).
RAW="$(SYS="$SYS" USERP="$USERP" LLM_TEMPERATURE=0.95 bash "$SK/scripts/llm-call.sh")"
[ -n "$RAW" ] || { echo "GEN_SCRIPT_FAILED (no LLM configured — see llm-call.sh)" >&2; exit 3; }

# parse TOPIC + SCRIPT + derive query, emit JSON, and append topic to the dedup ledger — all in python (portable)
ID="$ID" RAW="$RAW" LEDGER="$LEDGER" python3 - <<'PY'
import json, os, re
raw = os.environ['RAW'].strip()
topic = ""
lines = raw.splitlines()
body = []
for ln in lines:
    m = re.match(r'^\s*TOPIC:\s*(.+)$', ln)
    if m and not topic:
        topic = m.group(1).strip()
    else:
        body.append(ln)
script = "\n".join(body).strip()
if not topic: topic = "personal finance"
ql = topic.lower()
m = re.search(r'money|saving|invest|budget|debt|credit|retire|tax|income|wealth|stock|bank', ql)
query = m.group(0) if m else "money"
# append to ledger for dedup
with open(os.environ['LEDGER'], 'a') as f:
    f.write(json.dumps({'id': os.environ['ID'], 'topic': topic}, ensure_ascii=False) + "\n")
print(json.dumps({'id': os.environ['ID'], 'topic': topic, 'query': query, 'script': script}, ensure_ascii=False))
PY
