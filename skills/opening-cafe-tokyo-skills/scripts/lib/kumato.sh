#!/usr/bin/env bash
# lib/kumato.sh — kumato (新大久保) シェアキッチン scrape + 内見問合せ。
#
# kumato は飲食店営業許可 + 菓子製造業許可 両方取得済 (代替書類で通る ★★★)。
# Site: https://kumato.jp/ (要確認、実 URL は scrape 時に検出)
#
# Usage:
#   bash lib/kumato.sh status          → 空き status を Slack 報告
#   bash lib/kumato.sh inquire <date>  → 内見申請 (DOM パターンが定まったら自動 form 入力)
#
# 現状は status のみ実装。inquiry form は agent-{{profile.lateness.stakeholders.channel}} で 1 度手動操作後
# selector を確定してから auto 化する (DOM 確定済の kashispace/theghostrestaurant
# と同じパターン)。
#
# stdout final line:
#   ✅ kumato status: candidate=<count>
#   ❌ kumato FAILED: <reason>

set -uo pipefail

ACTION="${1:-status}"
SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
DATA_DIR="$SKILL/data/cafe"
mkdir -p "$DATA_DIR"

set -a; source "$HOME/.openclaw/.env"; set +a

PYTHON="python3"
AGENT_BROWSER="/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}"

LOG_DIR="$SKILL/output/$(date +%Y-%m-%d)_kumato"
mkdir -p "$LOG_DIR"

case "$ACTION" in
  status)
    URL="https://kumato.jp/"
    "$AGENT_BROWSER" open "$URL" >/dev/null 2>&1 || true
    sleep 3
    "$AGENT_BROWSER" snapshot text > "$LOG_DIR/status.txt" 2>/dev/null || echo "" > "$LOG_DIR/status.txt"
    LINES=$(wc -l < "$LOG_DIR/status.txt" | tr -d ' ')

    # candidate detection: look for "空き", "予約", "ご利用可能" etc keywords
    HITS=$(grep -cE "空き|空室|予約|ご利用可能|時間単位|シェアキッチン" "$LOG_DIR/status.txt" 2>/dev/null || echo 0)

    # Persist snapshot
    SNAPSHOT_FILE="$DATA_DIR/kumato-snapshots.json"
    [ -f "$SNAPSHOT_FILE" ] || echo '{"snapshots":[]}' > "$SNAPSHOT_FILE"
    $PYTHON - "$SNAPSHOT_FILE" "$LINES" "$HITS" "$LOG_DIR" <<'PY'
import sys, json, datetime, pathlib
p = pathlib.Path(sys.argv[1])
db = json.loads(p.read_text())
db["snapshots"].append({
    "captured_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "raw_lines": int(sys.argv[2]),
    "candidate_keyword_hits": int(sys.argv[3]),
    "log_dir": sys.argv[4],
})
db["snapshots"] = db["snapshots"][-20:]
p.write_text(json.dumps(db, ensure_ascii=False, indent=2))
PY

    # Slack 報告 (5/9 v27 fix)
    TS=$("$PYTHON" - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$HITS" "$LINES" "$LOG_DIR" <<'PY'
import sys, json, urllib.request
ch, token, hits, lines, logdir = sys.argv[1:6]
payload = {
    "channel": ch,
    "text": f"🏠 kumato status: candidate={hits}",
    "blocks": [
        {"type":"header","text":{"type":"plain_text","text":"🏠 cafe-kumato-status"}},
        {"type":"section","fields":[
            {"type":"mrkdwn","text":f"*candidate keyword hits:*\n{hits}"},
            {"type":"mrkdwn","text":f"*scrape lines:*\n{lines}"},
            {"type":"mrkdwn","text":"*site:*\nkumato.jp"},
            {"type":"mrkdwn","text":"*type:*\nshare-kitchen 飲食店+菓子製造許可済"},
        ]},
        {"type":"context","elements":[{"type":"mrkdwn","text":f"log: `{logdir}`"}]},
    ]
}
req = urllib.request.Request(
    "https://slack.com/api/chat.postMessage",
    data=json.dumps(payload).encode(),
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json; charset=utf-8"},
    method="POST")
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(json.loads(r.read().decode()).get("ts","?"))
except Exception:
    print("?")
PY
)
    echo "✅ kumato status: candidate=$HITS lines=$LINES | slack ts=$TS"
    ;;

  inquire)
    DATE="${2:?usage: kumato.sh inquire <YYYY-MM-DD>}"
    echo "⏳ kumato inquire form auto-fill not yet implemented (DOM selector needed)"
    echo "  manual fallback: agent-{{profile.lateness.stakeholders.channel}} open https://kumato.jp/ → 内見問合せフォーム"
    echo "  TODO: capture DOM selector once → automate"
    echo "❌ kumato inquire FAILED: not implemented"
    exit 1
    ;;

  *)
    echo "❌ kumato FAILED: unknown action '$ACTION'"
    exit 1
    ;;
esac
