#!/usr/bin/env bash
# x-repost-cli.sh — ONE daily pass of the X quote-tweet loop, then exit.
#
# Cadence is owned by launchd (skills/x-repost/launchd/ai.anicca.x-repost-pass.plist), not by
# this script and not by a tmux core: one pass runs, publishes at most one quote tweet, reports,
# and exits. That is the gig-pass shape (run_with_cdp_lock -> worker -> exit), not the
# always-on affiliate/explorer tmux shape, because there is nothing to keep warm between passes.
#
# Pipeline: registry gate -> lease browser -> recon X -> select+draft (model) -> humanize
# (a SEPARATE model call, style only) -> choose (model) -> publish via CDP -> record -> Telegram.
#
# Nothing is recorded and nothing is reported as published unless x_post.py read the permalink
# back off the account timeline. There is no dry-run mode: a pass either ships a real post or
# says why it did not.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"

SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SKILL/../.." && pwd)"
# State must outlive the code it was written by. Once this skill runs from a read-only release
# directory keyed to a commit, a state dir inside the release would be discarded on every deploy --
# taking the posted ledger, and with it the duplicate protection, along with it.
STATE="${X_REPOST_STATE_DIR:-$SKILL/state}"
POSTED="$STATE/posted.jsonl"
PY=/opt/homebrew/bin/python3; [ -x "$PY" ] || PY=python3
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
CODEX="$(command -v codex || echo "$HOME/.local/bin/codex")"
IDENTITY="${X_REPOST_BROWSER_IDENTITY:-x:anicca}"
# x-repost is Codex-only: Claude's subscription ceiling must not be able to stall this loop.
MODEL="${X_REPOST_MODEL:-gpt-5.6-luna}"
REASONING_EFFORT="${X_REPOST_REASONING_EFFORT:-max}"
HUMANIZER_SKILL="${X_REPOST_HUMANIZER:-$HOME/.openclaw/skills/jp-humanizer-pro/SKILL.md}"
GUARD="$HOME/.config/ai/bin/browser-guard.sh"
WITH_BROWSER="$REPO_ROOT/skills/browser/with-browser.sh"
ENSURE_BROWSER="$HOME/anicca/skills/browser/ensure_provision_browser.sh"
LEASE_HELD=0

PASS_ID="$(date +%Y%m%dT%H%M%S)"
EV="$STATE/evidence/$PASS_ID"
mkdir -p "$EV" "$STATE"
touch "$POSTED"

log() { echo "$(date '+%F %T') x-repost[$PASS_ID]: $*"; }

# Same channel/target every other migrated cron reports to (chat 0000000000 = Dais), but the
# response is kept: telegram-notify.sh discards it, and a report whose messageId was thrown away
# cannot be told apart from one that never arrived.
send_telegram() {
  openclaw message send --channel telegram --target "${TELEGRAM_ALERT_CHAT_ID:-0000000000}" \
    -m "$1" --json >>"$EV/telegram.jsonl" 2>&1
}

# A published post whose report never arrived is indistinguishable from a pass that did nothing.
# The send is occasionally flaky on its own (2026-08-17 14:42: post shipped, report did not, while
# a manual send seconds later went through), so it retries and then survives in a backlog that the
# next pass flushes.
report() {
  # The sender is this loop, not the interactive session that happened to write it, and not a
  # vendor. With hundreds of loops reporting into one thread the useful identity is WHICH LOOP,
  # and a hardcoded model name would start lying the moment someone runs this on another model.
  local body="x-repost::: $1

— loop x-repost · model ${MODEL} · effort ${REASONING_EFFORT} · pass ${PASS_ID}"
  for attempt in 1 2 3; do
    if send_telegram "$body"; then
      return 0
    fi
    sleep 3
  done
  log "telegram report failed 3x, queued to backlog"
  "$PY" -c 'import json,sys; open(sys.argv[1],"a",encoding="utf-8").write(json.dumps({"body": sys.argv[2]}, ensure_ascii=False)+"\n")' \
    "$STATE/report-backlog.jsonl" "$body"
}

flush_report_backlog() {
  [ -s "$STATE/report-backlog.jsonl" ] || return 0
  local pending="$STATE/report-backlog.jsonl" kept="$STATE/report-backlog.tmp"
  : >"$kept"
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    local body
    body="$("$PY" -c 'import json,sys; print(json.loads(sys.argv[1])["body"])' "$line" 2>/dev/null)" || continue
    if send_telegram "$body"; then
      log "flushed a queued report"
    else
      printf '%s\n' "$line" >>"$kept"
    fi
  done <"$pending"
  mv "$kept" "$pending"
}

# A pass that went wrong and left no trace teaches nothing. One line, appended, never blocking.
lesson() {
  "$PY" -c 'import json,sys,datetime; open(sys.argv[1],"a",encoding="utf-8").write(json.dumps({"ts": datetime.datetime.now().astimezone().isoformat(), "pass_id": sys.argv[2], "what_happened": sys.argv[3], "lesson": sys.argv[4]}, ensure_ascii=False)+"\n")' \
    "$STATE/lessons.jsonl" "$PASS_ID" "$1" "$2" 2>/dev/null || true
}

finish() {
  local rc="$1"; shift
  log "$*"
  # Heartbeat marks "a pass ran to a decision", not "a post shipped" -- a legitimately quiet day
  # (no worthwhile candidate) must not read as a dead loop to the healthcheck.
  [ "$rc" -eq 0 ] && touch "$STATE/.last-pass"
  if [ "$LEASE_HELD" -eq 1 ]; then
    bash "$GUARD" release "$IDENTITY" >/dev/null 2>&1 || true
    LEASE_HELD=0
  fi
  exit "$rc"
}

# Every Codex call in this loop is one-shot, Luna/max, and must end in a JSON object. Anything else
# is a failed step -- the prompt is never "retried creatively", the pass just stops.
ask_model() {
  local prompt_file="$1" out_file="$2"
  # Bounded, because the cadence is hourly and a model call has no natural end. On 2026-08-19 a
  # single pass spent over half an hour across three calls, which on this schedule means two passes
  # driving the same browser at once. A call that overruns is a failed step, not a slow one.
  timeout "${X_REPOST_MODEL_TIMEOUT:-600}" \
    env -u ANTHROPIC_API_KEY "$CODEX" exec --ephemeral --model "$MODEL" \
    -c "model_reasoning_effort=\"$REASONING_EFFORT\"" --ignore-user-config --json \
    -o "$out_file" --dangerously-bypass-approvals-and-sandbox \
    --skip-git-repo-check -C "$SKILL" --add-dir "$SKILL" \
    "$(cat "$prompt_file")" >"$EV/model.stdout" 2>>"$EV/model.err"
  "$PY" - "$out_file" <<'PYEOF'
import json, re, sys
raw = open(sys.argv[1], encoding="utf-8", errors="replace").read()
blocks = re.findall(r"\{.*\}", raw, re.S)
for candidate in reversed(blocks):
    for start in range(len(candidate)):
        try:
            json.dump(json.loads(candidate[start:]), sys.stdout, ensure_ascii=False)
            raise SystemExit(0)
        except json.JSONDecodeError:
            continue
raise SystemExit(1)
PYEOF
}

# ---------------------------------------------------------------- gate: CEO registry + budget
# shellcheck source=/dev/null
source "$REPO_ROOT/lib/registry-enforce.sh"
registry_enforce_or_exit x-repost

# Do this before the hourly guard: a pass with nothing to publish is still a chance to deliver a
# report that an earlier pass could not.
flush_report_backlog

# ---------------------------------------------------------------- gate: at most one post per hour
# Cadence is hourly, so the guard is hourly too. The daily ceiling stays as a runaway brake only:
# it is not the intended rhythm, it is what stops a scheduling bug from emptying the account's
# credibility in one afternoon.
THIS_HOUR="$(date +%Y-%m-%dT%H)"
TODAY="$(date +%F)"
# Count only rows that actually reached X. A row recorded as not_posted proves the opposite --
# letting it hold the hourly slot would turn one failed attempt into a silent hour of no output.
read -r HOUR_COUNT TODAY_COUNT <<<"$("$PY" - "$POSTED" "$THIS_HOUR" "$TODAY" <<'PYEOF'
import json, sys
path, this_hour, today = sys.argv[1:4]
hour = day = 0
try:
    lines = open(path, encoding="utf-8").read().splitlines()
except OSError:
    lines = []
for line in lines:
    line = line.strip()
    if not line:
        continue
    try:
        row = json.loads(line)
    except json.JSONDecodeError:
        continue
    if row.get("status") == "not_posted":
        continue
    at = row.get("posted_at", "")
    hour += at.startswith(this_hour)
    day += at.startswith(today)
print(hour, day)
PYEOF
)"
if [ "${HOUR_COUNT:-0}" -gt 0 ]; then
  log "already published this hour ($THIS_HOUR) -- nothing to do"
  touch "$STATE/.last-pass"
  exit 0
fi
if [ "${TODAY_COUNT:-0}" -ge "${X_REPOST_DAILY_MAX:-12}" ]; then
  log "daily ceiling reached ($TODAY_COUNT/${X_REPOST_DAILY_MAX:-12}) -- nothing to do"
  touch "$STATE/.last-pass"
  exit 0
fi

set -a
# shellcheck source=/dev/null
. "$HOME/.openclaw/.env" 2>/dev/null
set +a
if [ -z "${TWITTER_AUTH_TOKEN:-}" ]; then
  report "❌ TWITTER_AUTH_TOKEN unset — cannot restore the X session"
  finish 1 "TWITTER_AUTH_TOKEN unset"
fi

# ---------------------------------------------------------------- browser (leased, never :9222)
CDP="$(AI_BROWSER_HOLDER_PID=$$ bash "$ENSURE_BROWSER" "$IDENTITY" 2>>"$EV/browser.err")"
case "$CDP" in
  http*) LEASE_HELD=1; log "leased $IDENTITY at $CDP" ;;
  *) log "browser unavailable for $IDENTITY (see $EV/browser.err) -- skipping this pass"
     report "⚠️ ブラウザ($IDENTITY)を確保できずパスを見送り: $(tail -1 "$EV/browser.err" 2>/dev/null)"
     exit 0 ;;
esac
trap 'if [ "$LEASE_HELD" -eq 1 ]; then bash "$GUARD" release "$IDENTITY" >/dev/null 2>&1 || true; fi' EXIT

# ---------------------------------------------------------------- 1. recon
if ! "$UV" run --quiet "$SKILL/scripts/x_collect.py" --cdp "$CDP" --mode recon \
      --queries "$SKILL/config/queries.txt" --posted "$POSTED" >"$EV/candidates.json" 2>>"$EV/collect.err"; then
  report "❌ recon failed — $(tail -1 "$EV/collect.err" 2>/dev/null)"
  finish 1 "recon failed"
fi
CAND_COUNT="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["candidate_count"])' "$EV/candidates.json" 2>/dev/null || echo 0)"
log "collected $CAND_COUNT candidates"
if [ "${CAND_COUNT:-0}" -eq 0 ]; then
  report "⚠️ 候補 0 件（検索 $(wc -l <"$SKILL/config/queries.txt") クエリを実走したが該当なし）。DOM セレクタ変更を疑う。"
  lesson "候補0件" "検索が0件を返し続けるなら話題不足でなく data-testid 変更を先に疑う"
  finish 0 "no candidates"
fi

# ---------------------------------------------------------------- 2. engagement feedback
"$UV" run --quiet "$SKILL/scripts/x_collect.py" --cdp "$CDP" --mode engagement \
  --posted "$POSTED" >"$EV/engagement.json" 2>>"$EV/collect.err" || log "engagement refresh failed (non-fatal)"

# Recon is complete. Drafting and model selection do not use the browser, so return the shared
# identity immediately. Publishing acquires it again for exactly the mutation + readback lifetime.
bash "$GUARD" release "$IDENTITY" >/dev/null 2>&1 || true
LEASE_HELD=0
CDP=""

# top performers become the few-shot for this pass (most recent 10 considered, best 5 shown)
"$PY" - "$POSTED" >"$EV/fewshot.json" <<'PYEOF'
import json, sys
rows = []
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    try:
        r = json.loads(line)
    except json.JSONDecodeError:
        continue
    if r.get("post_url"):
        rows.append(r)
rows = rows[-10:]
rows.sort(key=lambda r: (r.get("engagement") or {}).get("likes", 0), reverse=True)
json.dump([{"tone": r.get("tone"), "text": r.get("text"),
            "engagement": r.get("engagement") or {}} for r in rows[:5]],
          sys.stdout, ensure_ascii=False, indent=1)
PYEOF

# ---------------------------------------------------------------- 3. select + draft
# The well, minus anything published in the last 14 days. A file the loop only reads has a bottom:
# 29 posts came out of three anecdotes because voice.md never changed. Seeds are state now.
SEEDS="$STATE/seeds.jsonl"
[ -s "$SEEDS" ] || "$PY" "$SKILL/scripts/x_seeds.py" --seeds "$SEEDS" \
  --bootstrap "$SKILL/config/voice.md" >/dev/null 2>&1
"$PY" "$SKILL/scripts/x_seeds.py" --seeds "$SEEDS" --available >"$EV/seeds-available.json" 2>/dev/null \
  || echo "[]" >"$EV/seeds-available.json"
SEEDS_AVAILABLE="$("$PY" -c 'import json,sys; print(len(json.load(open(sys.argv[1]))))' "$EV/seeds-available.json" 2>/dev/null || echo 0)"
log "seeds available: $SEEDS_AVAILABLE"

# Which action this pass takes. Held in state so the ratio can be moved by measurement rather than
# by editing code: X prices "the author engaged your reply" at 75 and a like at 0.5, so a reply is
# the action worth buying -- but that is reasoned from published weights, not yet proven here, and
# a knob is how it gets proven.
STRATEGY="$STATE/strategy.json"
[ -s "$STRATEGY" ] || printf '{"reply_ratio": %s, "note": "share of passes that reply instead of quote"}\n' \
  "${X_REPOST_DEFAULT_REPLY_RATIO:-0.75}" >"$STRATEGY"
KIND="$("$PY" - "$STRATEGY" <<'PYEOF'
import json, random, sys
try:
    ratio = float(json.load(open(sys.argv[1], encoding="utf-8")).get("reply_ratio", 0.75))
except Exception:
    ratio = 0.75
print("reply" if random.random() < max(0.0, min(1.0, ratio)) else "quote")
PYEOF
)"
TARGET_TONE="$("$PY" -c 'import json,random,sys
w=(json.load(open(sys.argv[1])).get("tone_weights") or {"primary":1,"empathy":1,"funny":1})
ks=list(w); print(random.choices(ks,[max(0.0,float(w[k])) for k in ks])[0])' "$STRATEGY" 2>/dev/null || echo primary)"
log "target tone: $TARGET_TONE"
log "action this pass: $KIND (reply_ratio=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("reply_ratio"))' "$STRATEGY" 2>/dev/null))"

{
  cat <<'EOF'
あなたは X アカウント @selawmqt（sela | AI Tools）の運用者。AI/crypto の話題に「のっかり引用ツイート」を1日1本だけ出す。

## いまやること
1. 候補一覧から、引用する価値のある投稿を **1本だけ** 選ぶ。
2. その投稿への引用コメントを **3案** 書く（面白系 / 共感系 / 静かな一次情報系）。

## 選定基準
- 伸びていて、かつ議論を呼んでいる（数字は candidates[].metrics を見る。regex ではなくお前の判断で選ぶ）。
- **のっかれる AI / crypto の技術・実務の話題であること。**
- 次は必ず除外する: 個人攻撃・誹謗中傷・政治対立・事件性の高い炎上・人の不幸・訃報・センシティブな属性の話。
- 迷ったら選ばない。該当なしなら {"selected": false, "reason": "..."} だけを返す。

## 3案が必ず守ること
1. 相手をディスらない（否定・反論・訂正から入らない）
2. ポジティブな話を入れる
3. 自分にしかできない話をする（下の一次情報の種からのみ引く。無いことは書かない）
4. 自分の話をしすぎない
5. アクションにつなげる（読んだ人が次に何を見ればいいか）

構成: 共感1〜2文 → 自虐ひとつまみ → 自分だけが言える具体情報ひとつ。
分量の比率は 共感5 / 自虐3 / 一次情報2。ハッシュタグと絵文字は使わない。

## 言語（最重要）
**引用元と同じ言語で書く。** 英語の投稿には英語、日本語の投稿には日本語。
引用ツイートを読むのは元投稿の読者なので、言語が違えば誰にも届かない。
判別できない・混在している場合は **英語**。このアカウントは bio も既存投稿も英語で、
売る相手（affiliate / アプリ / creator 向け）も英語話者が中心。日本語ソースを選んだ時だけ日本語で書く。

## ここで失敗している（直近5本すべてに出た欠陥。同じ書き方をするな）

**書き出しを「うち」で始めるな。** 直近5本が全部「うちの/うちも/うちは」で始まっていた。
これは④の違反で、読み手には「自分語りが始まった」としか見えない。**1文目は相手の話**にする。

**種を数値のまま貼るな。** 実際に出た悪い例:

> うちは自動化を積み上げすぎてMacのlaunchd agentが244個、registered=Falseが173個・disabledが61個。

読む人は私の機械の内訳を知らないし、知りたくもない。種は**その人にとって何を意味するか**に翻訳して使う。
数字を出すなら **1つだけ**、意味が伝わるものに絞る。良い形:

> 増やすのは一瞬で、数えるのは後回しになる。気づいたら自分でも把握できない数になってた。

**内部用語を持ち込むな。** 引用元がその語を使っていない限り、次は書かない:
CDPポート / data-testid / exit 0 / BSDのmv / launchd / registered=False / lease / symlink。
自分の環境でしか通じない語は、その分野の人にも「内輪の話」に見える。

**自分に言及するのは1箇所まで。** 種は主張の根拠として1回出すだけで、主語を自分に戻さない。

## 長さ（超えると物理的に投稿できない）
X の上限は 280 で、**日本語や全角文字は1文字が2と数えられる**。引用元URLが23を消費するので本文は 230 まで。
つまり **英語なら約220文字、日本語なら115字**。3案すべてこの中に収める。
長い案は具体情報ではなく修飾語を削って縮める。

## 出力（最後に JSON オブジェクトだけを1つ）
{"selected": true, "source_url": "...", "why": "選んだ理由1文", "seed_id": "v00X または null",
 "drafts": [{"tone":"funny","text":"..."},{"tone":"empathy","text":"..."},{"tone":"primary","text":"..."}]}
EOF
  echo
  if [ "$KIND" = "reply" ]; then
    cat <<'EOF'
## 今回の形式: 返信（引用ツイートではない）
元投稿の会話の中に短い返信を置く。読むのは元投稿の読者と著者本人。
狙いは **著者が返したくなること** — X が最も高く評価するのは「返信に著者が反応した」状態で、
いいねの150倍の重みが付く。したがって:
- URL は貼らない（会話に既に紐づいているし、リンクは到達性を下げる）
- 著者が一言で答えられる形にする: 具体的な問い / 自分の実測値の提示 / 否定しない補足
- 「勉強になります」「同感です」だけの返信は書かない（答える理由が無い）
- 相手の投稿を要約し直さない
EOF
  else
    cat <<'EOF'
## 今回の形式: 引用ツイート
自分のタイムラインに新しい投稿として出し、末尾に引用元URLを置く（URLは投稿処理が付ける）。
EOF
  fi
  echo; echo "## 一次情報の種（この一覧の事実だけ使う。使ったら seed_id を返す）"
  echo "直近14日に使った種は除外済み。合う種が無ければ ③ を捨てて ①②④⑤ だけで書き、seed_id は null にする。
**その場合、一般論に逃げるな。** 「設計思想は筋が通っている」「今後が楽しみ」の類は何も言っていない。
種が無い時は **引用元の中身に踏み込む**: 相手が挙げた具体（数字・固有名・手順）を1つ拾い、
それがなぜ効くのか / どこで効かないのかを1文で言う。相手の投稿の要約は書かない。"
  cat "$EV/seeds-available.json"
  echo; echo "## 過去に伸びた自分の投稿（文体の参考。内容の再利用はしない）"; cat "$EV/fewshot.json"
  echo; echo "## 候補一覧"; cat "$EV/candidates.json"
} >"$EV/prompt-select.txt"

if ! ask_model "$EV/prompt-select.txt" "$EV/select.raw" >"$EV/select.json"; then
  # Distinguish "the model refused/failed" from "the account ran out of budget" -- the second is
  # not a bug in this loop and needs a human to raise a limit, so it must not read as a parse error.
  # 2026-08-17 13:35 lost a pass to exactly this, reported as "unparseable output".
  if grep -qi "spend limit\|usage limit\|rate limit" "$EV/select.raw" 2>/dev/null; then
    report "🛑 モデルの上限に当たってパスを見送り: $(head -c 200 "$EV/select.raw")"
    lesson "モデル上限でパス見送り" "ループ側では直せない。上限を上げるまで一定割合のパスが落ちる"
    finish 0 "model budget exhausted"
  fi
  report "❌ 選定/生成の応答が JSON として読めなかった: $(head -c 200 "$EV/select.raw")"
  finish 1 "select step returned unparseable output"
fi
SELECTED="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("selected"))' "$EV/select.json")"
if [ "$SELECTED" != "True" ]; then
  REASON="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("reason",""))' "$EV/select.json")"
  report "⚠️ 今回は該当なしで見送り: $REASON"
  finish 0 "model selected nothing"
fi

# ---------------------------------------------------------------- 4. humanize (separate call)
{
  echo "以下の各案について、**内容は一切変えず文体だけ**を直せ。事実・数値・固有名詞・主張・情報量を足しても引いてもいけない。"
  echo
  # Use the house humanizer rather than a private copy of one. jp-humanizer-pro already exists and
  # is maintained; a second checklist living here would drift from it, and the drifting one is the
  # one this loop would keep using.
  if [ -r "$HUMANIZER_SKILL" ]; then
    cat "$HUMANIZER_SKILL"
  else
    echo "（jp-humanizer-pro が見つからないので同梱の簡易版を使う）"
    cat "$SKILL/config/humanize-checklist.md"
  fi
  echo; echo "## 入力（この drafts を直す）"
  "$PY" -c 'import json,sys; json.dump(json.load(open(sys.argv[1]))["drafts"], sys.stdout, ensure_ascii=False, indent=1)' "$EV/select.json"
  echo; echo
  echo '## 出力（最後に JSON オブジェクトだけを1つ）'
  echo '{"drafts":[{"tone":"funny","text":"..."},{"tone":"empathy","text":"..."},{"tone":"primary","text":"..."}]}'
} >"$EV/prompt-humanize.txt"

if ! ask_model "$EV/prompt-humanize.txt" "$EV/humanize.raw" >"$EV/humanized.json"; then
  report "❌ humanize の応答が JSON として読めなかった"
  finish 1 "humanize step returned unparseable output"
fi

# ---------------------------------------------------------------- 5. choose one
{
  echo "次の3案から、引用ツイートとして実際に投稿する1案を選べ。"
  echo "基準: 相手をディスっていない / ポジティブ / 自分にしか言えない具体が入っている / 自分語りが過剰でない / 次の行動につながる / AI 文体でない。"
  echo
  echo "## 今回 優先するトーン: $TARGET_TONE"
  echo "同点か僅差ならこのトーンを選ぶ。明確に品質が落ちる場合だけ他を選び、その理由を why に書く。"
  echo "（理由: 29投稿中25本が同じトーンで、どのトーンが伸びるかを比べる材料が無い。"
  echo "  比率は strategy.json が持ち、実測の初速で更新される。）"
  echo; echo "## 引用元"; "$PY" -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["source_url"]); print(d.get("why",""))' "$EV/select.json"
  echo; echo "## 3案"; cat "$EV/humanized.json"
  echo; echo '## 出力（最後に JSON オブジェクトだけを1つ）'
  echo '{"tone":"...","text":"実際に投稿する本文そのまま","why":"選んだ理由1文"}'
} >"$EV/prompt-choose.txt"

if ! ask_model "$EV/prompt-choose.txt" "$EV/choose.raw" >"$EV/chosen.json"; then
  report "❌ 最終選択の応答が JSON として読めなかった"
  finish 1 "choose step returned unparseable output"
fi

# Enforce X's real limit before touching the browser. Every failed publish so far was an
# over-length post: X disables the Post button and the click is a silent no-op, so an oversized
# draft costs a whole pass and looks like a browser bug. Japanese counts 2 per character and the
# quoted URL costs 23, so the budget is far tighter than a naive character count suggests.
if ! "$PY" - "$EV/chosen.json" "$EV/humanized.json" "$EV/post.txt" "${X_REPOST_TEXT_BUDGET:-250}" \
     >"$EV/length.json"; then
  report "⚠️ 3案とも X の文字数上限を超えていたので今回は見送り（$(cat "$EV/length.json" 2>/dev/null | head -c 200)）"
  lesson "3案とも文字数超過" "日本語は1文字2カウント。プロンプトの上限表記が実単位とずれていないか見る"
  finish 0 "all drafts over the X length budget"
fi <<'PYEOF'
import json, sys, unicodedata

chosen_path, humanized_path, out_path, budget = sys.argv[1:5]
budget = int(budget)


def weighted(text):
    """X counts full-width characters as 2. A plain len() is not the limit X enforces."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)


chosen = json.load(open(chosen_path, encoding="utf-8"))
candidates = [(chosen.get("tone", ""), (chosen.get("text") or "").strip())]
try:
    for d in json.load(open(humanized_path, encoding="utf-8"))["drafts"]:
        candidates.append((d.get("tone", ""), (d.get("text") or "").strip()))
except Exception:
    pass

fitting = [(t, x) for t, x in candidates if x and weighted(x) <= budget]
if not fitting:
    json.dump({"ok": False, "budget": budget,
               "weights": [{"tone": t, "weighted": weighted(x)} for t, x in candidates if x]},
              sys.stdout, ensure_ascii=False)
    raise SystemExit(1)

# Prefer the model's own pick; fall back to the longest draft that still fits, because length is
# the only axis being traded here and the longest surviving draft keeps the most substance.
tone, text = fitting[0] if fitting[0] == candidates[0] else max(fitting, key=lambda p: weighted(p[1]))
open(out_path, "w", encoding="utf-8").write(text)
json.dump({"ok": True, "tone": tone, "weighted": weighted(text), "budget": budget,
           "substituted": (tone, text) != candidates[0]}, sys.stdout, ensure_ascii=False)
PYEOF
log "length gate: $(cat "$EV/length.json")"
SOURCE_URL="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["source_url"])' "$EV/select.json")"
TONE="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["tone"])' "$EV/length.json")"
if [ ! -s "$EV/post.txt" ] || [ -z "$SOURCE_URL" ]; then
  report "❌ 投稿本文または引用元 URL が空"
  finish 1 "empty text or source url"
fi

# Pull the quoted post's author and body back out of the candidate set. The report has to stand on
# its own in the Telegram thread -- a bare URL forces a trip to X just to see what was quoted.
"$PY" - "$EV/candidates.json" "$SOURCE_URL" >"$EV/source.json" <<'PYEOF'
import json, sys
url = sys.argv[2]
row = next((c for c in json.load(open(sys.argv[1], encoding="utf-8"))["candidates"]
            if c.get("url") == url), {})
m = row.get("metrics") or {}
json.dump({"handle": (row.get("handle") or "").strip(),
           "text": (row.get("text") or "").strip(),
           "metrics": f"♥{m.get('likes', '?')} 💬{m.get('replies', '?')} 🔁{m.get('reposts', '?')}"},
          sys.stdout, ensure_ascii=False)
PYEOF
SRC_HANDLE="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["handle"])' "$EV/source.json")"
SRC_TEXT="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["text"][:280])' "$EV/source.json")"
SRC_METRICS="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["metrics"])' "$EV/source.json")"

# ---------------------------------------------------------------- 6. publish
BROWSER_WAIT_SECONDS="${X_REPOST_PUBLISH_BROWSER_WAIT_SECONDS:-300}" \
  "$WITH_BROWSER" "$IDENTITY" -- "$UV" run --quiet "$SKILL/scripts/x_post.py" \
  --source-url "$SOURCE_URL" --text-file "$EV/post.txt" --mode "$KIND" >"$EV/post.json" 2>>"$EV/post.err"
PUBLISH_RC=$?
if [ "$PUBLISH_RC" -eq 2 ]; then
  # Submitted but unconfirmed. Claim the source_url in the ledger anyway: leaving it unclaimed is
  # what would make the next pass quote the same post a second time.
  X_REPOST_KIND="$KIND" "$PY" - "$POSTED" "$SOURCE_URL" "$TONE" "$EV/post.txt" "$EV/source.json" <<'PYEOF'
import json, os, sys, datetime
posted, source_url, tone, text_file, source_file = sys.argv[1:6]
src = json.load(open(source_file, encoding="utf-8"))
row = {"posted_at": datetime.datetime.now().astimezone().isoformat(),
       "source_url": source_url, "source_handle": src.get("handle", ""),
       "source_text": src.get("text", ""), "tone": tone, "kind": os.environ.get("X_REPOST_KIND", "quote"),
       "text": open(text_file, encoding="utf-8").read().strip(),
       "post_url": None, "status": "unverified"}
with open(posted, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
PYEOF
  report "$(printf '⚠️ 投稿は送ったが確認できなかった（重複防止のため引用元は消費済みにした）\n引用元: %s\n本文:\n%s' \
    "$SOURCE_URL" "$(cat "$EV/post.txt")")"
  lesson "投稿は送ったが確認できず" "composer は受理したのに読み戻せない。引用元は消費済みにして重複を防ぐ"
  finish 1 "publish unverified"
fi
if [ "$PUBLISH_RC" -ne 0 ]; then
  report "❌ 投稿失敗: $(head -c 300 "$EV/post.json" 2>/dev/null) $(tail -1 "$EV/post.err" 2>/dev/null)"
  lesson "投稿が送信されなかった" "composer が空にならない時は文字数上限か投稿ボタンの取り違えを疑う"
  finish 1 "publish failed rc=$PUBLISH_RC"
fi
POST_URL="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["post_url"])' "$EV/post.json")"

# ---------------------------------------------------------------- 7. record + report
X_REPOST_KIND="$KIND" "$PY" - "$POSTED" "$SOURCE_URL" "$TONE" "$EV/post.txt" "$POST_URL" "$EV/source.json" <<'PYEOF'
import json, os, sys, datetime
posted, source_url, tone, text_file, post_url, source_file = sys.argv[1:7]
src = json.load(open(source_file, encoding="utf-8"))
row = {"posted_at": datetime.datetime.now().astimezone().isoformat(),
       "kind": os.environ.get("X_REPOST_KIND", "quote"),
       "source_url": source_url,
       "source_handle": src.get("handle", ""),
       "source_text": src.get("text", ""),
       "tone": tone,
       "text": open(text_file, encoding="utf-8").read().strip(),
       "post_url": post_url}
with open(posted, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
PYEOF

KIND_JA="$([ "$KIND" = "reply" ] && echo "返信" || echo "引用ツイート")"
report "$(printf '✅ %s を投稿した\n\n── 元の投稿 ──\n%s  %s\n%s\n%s\n\n── 自分が書いた%s ──\n%s\n%s\n\nトーン: %s' \
  "$KIND_JA" "$SRC_HANDLE" "$SRC_METRICS" "$SRC_TEXT" "$SOURCE_URL" \
  "$KIND_JA" "$(cat "$EV/post.txt")" "$POST_URL" "$TONE")"
# ---------------------------------------------------------------- 8. keep the well from draining
# Mark what was spent, then try to refill. Both are best-effort: a well problem must never cost a
# post that already shipped.
SEED_USED="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("seed_id") or "")' "$EV/select.json" 2>/dev/null || echo "")"
if [ -n "$SEED_USED" ] && [ "$SEED_USED" != "None" ] && [ "$SEED_USED" != "null" ]; then
  "$PY" "$SKILL/scripts/x_seeds.py" --seeds "$SEEDS" --mark "$SEED_USED" >>"$EV/seeds.log" 2>&1 || true
  log "seed used: $SEED_USED"
fi

# Harvesting a new seed costs another model call, and on an hourly cadence that is the
# difference between a pass that fits in its hour and one that does not. The cooldown is
# fourteen days, so one new seed a day is plenty: the digest job does it.

bash "$REPO_ROOT/bin/record-cost-event.sh" x-repost "${X_REPOST_PASS_COST_USD:-0.12}" >/dev/null 2>&1 || true
finish 0 "published $POST_URL"
