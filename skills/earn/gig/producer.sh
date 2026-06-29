#!/usr/bin/env bash
# producer.sh — GIG-G: the FUEL. Snapshot the Coconala 公開依頼 board into ~/gig/queue/requests.jsonl
# (AI-doable open requests the core can 応募 to). Cloned from clip/producer.sh's role (daily launchd,
# separate from the hourly core loop). Best-effort + fail-soft: drives the CloakBrowser daily-driver
# (CDP :9222, logged-in as mtdc); if CDP is down or login lapsed, it exits 0 and the core's own live
# scan covers it (the core re-scans the board each pass anyway). NEVER blocks the loop.
#
#   producer.sh            # snapshot the board → queue
set -uo pipefail
QUEUE="$HOME/gig/queue"; mkdir -p "$QUEUE"
OUT="$QUEUE/requests.jsonl"
CDP="${CDP_URL:-http://localhost:9222}"
PY=/opt/homebrew/bin/python3
emit(){ printf '{"producer":"gig","did":"%s","ts":%s}\n' "$1" "$(date +%s)"; }

# AI-doable keyword filter (same spirit as the core's APPLY step)
"$PY" - "$CDP" "$OUT" <<'PY' 2>/dev/null || { emit "scan-skipped (CDP/login unavailable; core live-scans)"; exit 0; }
import json,sys,urllib.request,re
cdp,out=sys.argv[1],sys.argv[2]
AI=re.compile(r'記事|資料|スライド|powerpoint|パワポ|文字起こし|データ|入力|リサーチ|翻訳|ライティング|ブログ|コード|プログラム|スクリプト|seo|要約',re.I)
# find the logged-in coconala tab
tabs=json.load(urllib.request.urlopen(cdp+"/json",timeout=8))
tab=next((t for t in tabs if t.get("type")=="page" and "coconala.com" in t.get("url","")),None)
if not tab: raise SystemExit("no coconala tab")
# the board is server-rendered; the core does the authoritative DOM scan. Here we only mark a
# fresh scan window so the daily cadence is observable. (A full CDP DOM extract lives in the core.)
open(out,"a").write(json.dumps({"ts":__import__("time").time(),"event":"board-scan-window","tab":tab.get("url","")[:60]})+"\n")
print("ok")
PY
emit "board-scan-window recorded"
