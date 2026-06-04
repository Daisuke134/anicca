#!/usr/bin/env bash
# scan.sh — discover Lancers JIDs.
# Usage:
#   scan.sh                         → live Camofox scan, stdout = newline-separated JIDs
#   scan.sh --offline-fixture <p>   → read fixture JSON, skip Camofox entirely

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

# parse args
FIXTURE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --offline-fixture) FIXTURE="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# extract_jids: arg $1 = file path, or "-" to read camofox snapshot JSON from
# the SNAP_JSON env var. (A heredoc binds stdin, so the live path must NOT read
# sys.stdin — that would return the empty post-heredoc stream.)
extract_jids() {
  "$PYTHON" - "$1" <<'PY'
import json, re, sys, os
src = sys.argv[1]
raw = os.environ.get('SNAP_JSON', '') if src == '-' else open(src).read()
# camofox live snapshot JSON contains unescaped control chars → strict=False
d = json.loads(raw, strict=False)
snap = d.get('snapshot', '')
seen = []
for m in re.finditer(r'/work/detail/(\d+)', snap):
    jid = m.group(1)
    if jid not in seen:
        seen.append(jid)
    if len(seen) >= 15:
        break
print('\n'.join(seen))
PY
}

if [ -n "$FIXTURE" ]; then
  log "scan offline: $FIXTURE"
  test -r "$FIXTURE" || { err "fixture unreadable: $FIXTURE"; exit 2; }
  extract_jids "$FIXTURE"
  exit 0
fi

cf_health || { err "camofox down"; exit 3; }

# Live scan — rotate keyword by day-of-week (proven pattern from port-from source line 49)
DOW=$(date +%u)
KEYWORDS=("AI" "ChatGPT" "Python" "スクレイピング" "自動化" "GPT" "動画制作" "AI開発" "LINE Bot" "Web制作")
IDX=$(( (DOW - 1) % ${#KEYWORDS[@]} ))
KW="${LANCERS_KEYWORD:-${KEYWORDS[$IDX]}}"
KW_ENC=$("$PYTHON" -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$KW")
log "scan live keyword=$KW (DOW=$DOW idx=$IDX)"

TAB=$(cf_open "https://www.lancers.jp/work/search?keyword=${KW_ENC}&open=1")
[ -z "$TAB" ] && { err "tab open failed"; exit 4; }
log "tabId=$TAB"

sleep 10
SNAP=$(cf_snapshot "$TAB")
cf_close "$TAB"

SNAP_JSON="$SNAP" extract_jids -
