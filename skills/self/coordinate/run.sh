#!/usr/bin/env bash
# self/coordinate/run.sh — bot2bot info-sharing (#9/H6). Thin wrapper around the already-tested
# skills/_shared/lib/bot2bot.py (post/poll). A TOOL, not a decision: it posts what the model tells
# it and reads what peers already posted; it never decides what counts as "notable" itself.
#
# Env: ANICCA_ARGS (JSON, optional) — {"note": "<lesson to share>", "topic": "<earn-slot name, e.g.
# hl_trade>"}. With `note` -> shares a bot2bot-lesson issue (de-duped by title). Without `note` ->
# polls open bot2bot-lesson issues for `topic` (default "general") and prints up to 5 newest.
# Auth = gh (this process's own session; bot2bot.poll resolves the real login dynamically, §9 fix).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED="$HERE/../../_shared"
ARGS="${ANICCA_ARGS:-}"; [ -z "$ARGS" ] && ARGS='{}'

PYTHONPATH="$SHARED" python3 -c "
import json, sys
sys.path.insert(0, '$SHARED')
from lib.bot2bot import post, poll

args = {}
try:
    args = json.loads('''$ARGS''') or {}
except Exception:
    args = {}

note = (args.get('note') or '').strip()
topic = (args.get('topic') or 'general').strip() or 'general'

if note:
    # de-dupe at TOPIC granularity: post()'s title is '[bot2bot][<topic>][lesson]' with no
    # content snippet (unlike self/issue-dev's title-prefix dedup), so an exact-lesson dedup isn't
    # possible from the title alone. Reusing the already-tested poll() as the dedup check means: if
    # ANY open lesson already exists for this topic, don't pile on another — read it instead.
    existing = poll(slot=topic, kinds=['lesson'])
    if existing:
        print(f'[coordinate] already an open lesson for topic={topic!r} ({existing[0][\"issue_url\"]}) — not duplicating; read it instead.')
    else:
        url = post(slot=topic, kind='lesson', body_text=note)
        print(f'[coordinate] shared lesson on topic={topic!r}: {url}')
else:
    lessons = poll(slot=topic, kinds=['lesson'])
    if not lessons:
        print(f'[coordinate] no open bot2bot-lesson issues yet for topic={topic!r} — nothing to fold in.')
    else:
        lessons = sorted(lessons, key=lambda t: t.get('ts_created') or '', reverse=True)[:5]
        print(f'[coordinate] {len(lessons)} lesson(s) from the colony on topic={topic!r}:')
        for t in lessons:
            body = (t.get('body') or '').strip().replace(chr(10), ' ')[:200]
            print(f'  - {t[\"issue_url\"]}: {body}')
" 2>&1
exit 0
