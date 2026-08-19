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
TARGET="${TELEGRAM_ALERT_CHAT_ID:-0000000000}"
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
  echo "以下は実在の出力だけを貼ったものだ。ここに書かれていることからのみ、"
  echo "**読んだ人が自分の状況に当てはめられる教訓** を ${X_REPOST_HARVEST_COUNT:-5}件 取り出せ。"
  echo
  echo "## 種の形（守らないと使い物にならない）"
  echo "- 書き出しは **一般化した教訓**。内部の事実はその根拠として後ろに1つ置くだけ。"
  echo "- **変数名・設定値・ラベル・ファイル名・コマンド名を書かない**。"
  echo "  悪い例: 「tone_weights を 1.0/1.0/1.0 → 0.5/1.5/1.0 に変更」「registered=False が173個」"
  echo "  良い例: 「測る前に決めた重みは、たいてい実測と逆を向いている」"
  echo "         「増やすのは一瞬で数えるのは後回しになる。気づくと自分でも把握できない数になる」"
  echo "- 数字は **1つまで**。意味が伝わるものだけ残す。"
  echo "- この機械でしか通じない話にしない。同じ失敗を他の人が別の道具でやりうる形にする。"
  echo "- 観点を変えて複数取る: 同じ材料でも「何が起きたか」「なぜ気づけなかったか」「一般化すると何か」は別の種。"
  echo "- 貼られていない数値・日付・固有名詞を作ったら失格。書けるものが少なければ少なくてよい。"
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
  echo; echo '## 出力（最後に JSON 配列だけを1つ）'
  echo '[{"fact":"...","measured_on":"YYYY-MM-DD","source":"どのセクションから取ったか"}]'
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
  # The well drains far faster than it fills: the pass may publish up to twelve times a day and
  # each published post spends a seed, while this job used to add exactly one. Harvest several at
  # once, from different angles on the same material.
  ADDED=0
  while IFS= read -r seed; do
    [ -n "$seed" ] || continue
    printf '%s' "$seed" | "$PY" "$SKILL/scripts/x_seeds.py" --seeds "$SEEDS" --add \
      >>"$STATE/seeds.log" 2>&1 && ADDED=$((ADDED + 1))
  done < <("$PY" - "$STATE/last-harvest.json" <<'PYINNER'
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    raise SystemExit(0)
rows = data if isinstance(data, list) else [data]
for row in rows:
    if isinstance(row, dict) and (row.get("fact") or "").strip():
        print(json.dumps(row, ensure_ascii=False))
PYINNER
)
  echo "x-repost-digest: harvested $ADDED seed(s)"
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
