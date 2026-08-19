#!/usr/bin/env bash
# x-repost-digest.sh — send the daily digest through the same Telegram path the pass uses.
#
# Separate from the per-pass report on purpose: the pass answers "what did it just publish", this
# answers "is it working". Mixing them would bury the trend under the events.
#
# A failed send lands in the same backlog the next pass flushes, so a digest is never silently lost.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${X_REPOST_STATE_DIR:-$SKILL/state}"
PY=/opt/homebrew/bin/python3; [ -x "$PY" ] || PY=python3
TARGET="${TELEGRAM_ALERT_CHAT_ID:-8547730585}"
WINDOW="${X_REPOST_DIGEST_WINDOW_HOURS:-24}"

# Evaluate before reporting, so the digest carries today's verdict instead of yesterday's. The
# evaluator refuses to move the knob on thin data and records that refusal, which is the difference
# between a loop that learns and one that just fidgets.
"$PY" "$SKILL/scripts/x_evaluate.py" --state "$STATE" \
  --window-hours "${X_REPOST_EXPERIMENT_WINDOW_HOURS:-48}" --apply >/dev/null 2>&1 \
  || echo "x-repost-digest: evaluation failed, reporting anyway" >&2

# Refill the well once a day. It used to run inside the hourly pass, which added a second long
# model call to every publish and pushed one pass past 35 minutes on an hourly schedule. The
# cooldown is fourteen days, so a seed a day is more than the loop can spend.
SEEDS="$STATE/seeds.jsonl"
CLAUDE_BIN="$(command -v claude || echo "$HOME/.local/bin/claude")"
{
  echo "以下は実在の出力だけを貼ったものだ。ここに**書かれていること**からのみ、"
  echo "この運用者が実際に観測した具体的な事実を **1つ** 抜き出せ。"
  echo "条件: ①数値か日付か固有名詞を含む ②既存の種と内容が重複しない ③このループの配管以外の話題を優先する"
  echo "貼られていない数値・日付・固有名詞を書いたら失格。該当が無ければ {\"fact\": null} を返す。"
  echo; echo "## 既存の種"
  "$PY" "$SKILL/scripts/x_seeds.py" --seeds "$SEEDS" --available 2>/dev/null || echo "[]"
  echo; echo "## この loop の日次ダイジェスト（実測）"
  "$PY" "$SKILL/scripts/x_digest.py" --posted "$STATE/posted.jsonl" 2>/dev/null
  echo; echo "## この Mac の launchd 群（実測サマリ）"
  "$PY" "$SKILL/../../bin/launchd_inventory.py" --format json 2>/dev/null | "$PY" -c '
import json,sys,collections
try: a=json.load(sys.stdin)["agents"]
except Exception: sys.exit(0)
print("agents:",len(a))
print("registered:",dict(collections.Counter(x.get("registered") for x in a)))
print("state:",dict(collections.Counter(x.get("actual_state") for x in a)))' 2>/dev/null
  echo; echo "## 直近のパスのログ"
  tail -12 "${X_REPOST_LOG:-$HOME/.openclaw/logs/x-repost-pass.out.log}" 2>/dev/null
  echo; echo '## 出力（最後に JSON オブジェクトだけを1つ）'
  echo '{"fact":"...","measured_on":"YYYY-MM-DD","source":"どのセクションから取ったか"}'
} >"$STATE/last-harvest-prompt.txt"

if timeout "${X_REPOST_MODEL_TIMEOUT:-600}" env -u ANTHROPIC_API_KEY "$CLAUDE_BIN" \
     -p "$(cat "$STATE/last-harvest-prompt.txt")" --model "${X_REPOST_MODEL:-sonnet}" \
     --dangerously-skip-permissions >"$STATE/last-harvest.raw" 2>/dev/null; then
  "$PY" - "$STATE/last-harvest.raw" >"$STATE/last-harvest.json" <<'PYEOF'
import json, re, sys
raw = open(sys.argv[1], encoding="utf-8", errors="replace").read()
for candidate in reversed(re.findall(r"\{.*\}", raw, re.S)):
    for start in range(len(candidate)):
        try:
            json.dump(json.loads(candidate[start:]), sys.stdout, ensure_ascii=False)
            raise SystemExit(0)
        except json.JSONDecodeError:
            continue
raise SystemExit(1)
PYEOF
  if "$PY" -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("fact") else 1)' \
       "$STATE/last-harvest.json" 2>/dev/null; then
    "$PY" "$SKILL/scripts/x_seeds.py" --seeds "$SEEDS" --add <"$STATE/last-harvest.json" \
      >>"$STATE/seeds.log" 2>&1 && echo "x-repost-digest: harvested $(tail -1 "$STATE/seeds.log")"
  fi
fi

BODY="$("$PY" "$SKILL/scripts/x_digest.py" --posted "$STATE/posted.jsonl" --window-hours "$WINDOW")" || {
  echo "x-repost-digest: could not build the digest" >&2
  exit 1
}
MESSAGE="x-repost::: $BODY"

for attempt in 1 2 3; do
  if openclaw message send --channel telegram --target "$TARGET" -m "$MESSAGE" --json \
       >>"$STATE/digest.jsonl" 2>&1; then
    echo "x-repost-digest: sent"
    exit 0
  fi
  sleep 3
done

echo "x-repost-digest: send failed 3x, queued to backlog" >&2
"$PY" -c 'import json,sys; open(sys.argv[1],"a",encoding="utf-8").write(json.dumps({"body": sys.argv[2]}, ensure_ascii=False)+"\n")' \
  "$STATE/report-backlog.jsonl" "$MESSAGE"
exit 1
