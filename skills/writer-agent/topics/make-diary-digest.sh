#!/usr/bin/env bash
# make-diary-digest.sh — nightly: turn today's dev activity (git log + updated docs +
# session transcript sample) into ONE article topic card for lane A (#55, strengthened #55b).
# spec: docs/superpowers/specs/2026-07-14-article-earn-loop-ssot.md §7.1 (dev-digest段落) + §7.6
# #55/#55b, and docs/loop-engineering/53-devlog-to-article-pipelines-gh-research.md (GH prior-art
# research behind #55b: commit/diff alone is a known industry-wide dead end, mcp-commit-story's
# own finding -- context must also include unfinished-work, project purpose, and continuity).
#
# Handover deps are rejected by the spec (some days nobody writes one), so the material is
# 100% deterministic bash collection: today's git log across the 4 live repos, today's updated
# docs/loop-engineering + .claude/handovers markdown, a capped sample of today's session
# transcripts (~/.claude/projects/*/*.jsonl, every session is auto-recorded, no opt-in needed),
# plus three #55b context-injection sources (mcp-commit-story style: commit+chat+README+past
# journal): today's spec/plan TODO-table diff + currently-open TODOs (unfinished-work context,
# this repo's durable TaskList-equivalent), profitable-claude/README.md's head (30 lines,
# project purpose), and the past 7 days' devlog card angles (continuity -- do not repeat the
# same angle). Overall material is capped at 3000 lines; when a day runs long, git log is
# what gets trimmed (least essential once the context injections exist, usually the largest
# section) -- never the newer context sources.
# Extraction itself (材料 -> 教訓) is judgment, not regex, so it goes through the model boundary — but
# what gets WRITTEN to the queue card must pass a deterministic redaction gate first, because
# transcripts can and do contain secrets (this is the one step in this script that is NOT a
# rubber stamp: a hit here must block the write, not just warn).
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
set -uo pipefail

ARTICLE_DIR="$HOME/profitable-claude/skills/writer-agent"
MODEL_RUNNER="${ARTICLE_MODEL_RUNNER:-$ARTICLE_DIR/runtime/model-runner.sh}"
STATE_DIR="$ARTICLE_DIR/state"
TOPICS_DIR="$STATE_DIR/topics"
QUEUE_DIR="$TOPICS_DIR/queue"
LOG="$HOME/.openclaw/logs/article-diary-digest.log"
mkdir -p "$QUEUE_DIR" "$STATE_DIR" "$(dirname "$LOG")"
python3 "$ARTICLE_DIR/scripts/topic_state.py" --skill-dir "$ARTICLE_DIR" >>"$LOG" 2>&1 || {
  echo "FATAL: runtime topic state initialization failed" >&2
  exit 1
}

# ============================================================================
# STEP 3 (redaction gate) — deterministic, function-scoped so --test-redaction can drive it
# standalone with a negative test, per the spec's explicit requirement (7.1: "fake secret を
# 混ぜて FAIL する negative test 付きで実装"). Reads the candidate card text on stdin.
# Returns 0 = clean, 1 = a secret-shaped string was found (caller must NOT write the card).
# ============================================================================
redaction_scan() {
  local text
  text="$(cat)"
  local patterns=(
    'sk-[A-Za-z0-9]{16,}'
    'xox[a-z]-[A-Za-z0-9-]+'
    'Bearer [A-Za-z0-9._-]{16,}'
    '\-\-\-\-\-BEGIN'
    'AKIA[0-9A-Z]{16}'
    'password[[:space:]]*[:=]'
    "api[_-]?key[[:space:]]*[:=][[:space:]]*[\"'][^\"']{8,}"
    '0[789][0-9]-?[0-9]{4}-?[0-9]{4}'
  )
  local pat
  for pat in "${patterns[@]}"; do
    if printf '%s' "$text" | grep -E -q "$pat"; then
      echo "REDACTION FAIL: matched pattern: $pat" >&2
      return 1
    fi
  done
  return 0
}

if [ "${1:-}" = "--test-redaction" ]; then
  # Negative test (must FAIL) + positive test (must PASS). Exit 0 only if both behave correctly.
  DIRTY="internal notes
export ANTHROPIC_API_KEY=sk-$(head -c20 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c20)
end of notes"
  CLEAN="症状: launchd 経由の headless 実行で OAuth token refresh が失敗する。
誤った本能: プロセスが生きているから正常と思い込む。
正しい手: CLIProxyAPI 経由のプレーンファイル資格情報にフォールバックする。
一般法則: 自己申告(プロセス生存)は証拠でない。exit code と実際の応答を見る。"

  OK=1
  if printf '%s' "$DIRTY" | redaction_scan 2>/tmp/redaction-test-dirty.log; then
    echo "[test-redaction] FAIL: dirty text was NOT caught (expected REDACTION FAIL)"
    OK=0
  else
    echo "[test-redaction] PASS: dirty text correctly caught -> $(cat /tmp/redaction-test-dirty.log)"
  fi
  if printf '%s' "$CLEAN" | redaction_scan 2>/tmp/redaction-test-clean.log; then
    echo "[test-redaction] PASS: clean text correctly passed through"
  else
    echo "[test-redaction] FAIL: clean text was wrongly flagged -> $(cat /tmp/redaction-test-clean.log)"
    OK=0
  fi
  rm -f /tmp/redaction-test-dirty.log /tmp/redaction-test-clean.log
  [ "$OK" -eq 1 ] && exit 0 || exit 1
fi

COLLECT_ONLY=0
[ "${1:-}" = "--collect-only" ] && COLLECT_ONLY=1

echo "=== make-diary-digest run $(date '+%F %T %Z') ===" >>"$LOG"

# Idempotent: a card for today already exists -> nothing to do, and no need to spend a
# model judge call finding that out. Checked across queue/in-progress/done (not queue alone):
# once a card moves out of queue/ into in-progress/ or done/, its basename disappears from
# queue/ and a stale/rerun invocation would otherwise regenerate a duplicate same-date card.
CARD_BASENAME="$(date +%F)-devlog.md"
CARD_PATH="$QUEUE_DIR/$CARD_BASENAME"
if [ "$COLLECT_ONLY" -eq 0 ]; then
  for d in "$QUEUE_DIR" "$TOPICS_DIR/in-progress" "$TOPICS_DIR/done"; do
    [ -d "$d" ] || continue
    if [ -f "$d/$CARD_BASENAME" ]; then
      echo "SKIP: $d/$CARD_BASENAME already exists (idempotent no-op)"
      echo "=== make-diary-digest SKIP (card exists) $(date '+%F %T %Z') ===" >>"$LOG"
      exit 0
    fi
  done
fi

# ============================================================================
# STEP 1 (collection, deterministic) — today's git log (4 live repos) + today's updated docs
# + a capped session-transcript sample. No handover dependency (spec: some days none exists).
# ============================================================================
MATERIAL_FILE="$STATE_DIR/.digest-material-$(date +%F).txt"
: > "$MATERIAL_FILE"
COMMIT_COUNT=0
DOC_COUNT=0
TRANSCRIPT_LINES=0
DOC_PATHS=()

# Git log goes to its OWN temp file, not directly into MATERIAL_FILE: the #55b overall cap
# (below) must trim from the git-log side specifically when the day's material runs long
# (team-lead instruction, spec §7.6 #55b row) -- git log is usually the bulk of the material
# and the least essential once the newer context sections (TODO/README/past-cards) exist, so
# it is what gets cut, never the new context injections.
GITLOG_TMP="$(mktemp)"
for repo in "$HOME/anicca-project" "$HOME/anicca" "$HOME/.openclaw" "$HOME/profitable-claude"; do
  [ -d "$repo/.git" ] || continue
  OUT="$(git -C "$repo" log --since=midnight --pretty='%h %s%n%b' 2>/dev/null)"
  if [ -n "$OUT" ]; then
    { printf '=== GIT LOG: %s ===\n' "$repo"; printf '%s\n\n' "$OUT"; } >>"$GITLOG_TMP"
    N=$(printf '%s\n' "$OUT" | grep -cE '^[0-9a-f]{7,40} ' || true)
    COMMIT_COUNT=$((COMMIT_COUNT + N))
  fi
done

while IFS= read -r f; do
  [ -f "$f" ] || continue
  { printf '=== DOC: %s ===\n' "$f"; cat "$f"; printf '\n\n'; } >>"$MATERIAL_FILE"
  DOC_COUNT=$((DOC_COUNT + 1))
  DOC_PATHS+=("$f")
done < <(find "$HOME/anicca-project/docs/loop-engineering" "$HOME/anicca-project/.claude/handovers" -type f -name '*.md' -mtime -1 2>/dev/null)

TRANSCRIPT_TMP="$(mktemp)"
while IFS= read -r f; do
  [ -f "$f" ] || continue
  jq -r 'select(.type=="user") | .message.content | if type=="array" then .[0].text? // empty else . end' "$f" 2>/dev/null
done < <(find "$HOME/.claude/projects" -maxdepth 2 -type f -iname '*.jsonl' -mtime -1 2>/dev/null) >>"$TRANSCRIPT_TMP"
head -1500 "$TRANSCRIPT_TMP" >"${TRANSCRIPT_TMP}.capped"
TRANSCRIPT_LINES=$(wc -l <"${TRANSCRIPT_TMP}.capped" | tr -d ' ')
if [ "$TRANSCRIPT_LINES" -gt 0 ]; then
  { echo "=== SESSION TRANSCRIPT SAMPLE (user turns only, capped 1500 lines) ==="; cat "${TRANSCRIPT_TMP}.capped"; echo; } >>"$MATERIAL_FILE"
fi
rm -f "$TRANSCRIPT_TMP" "${TRANSCRIPT_TMP}.capped"

# ============================================================================
# STEP 1b (#55b, context injection — docs/loop-engineering/53-devlog-to-article-pipelines-
# gh-research.md "具体反映"): commit/diff/transcript alone is a known-industry-wide dead end
# (mcp-commit-story's own finding). Add the same three context sources that repo uses:
# unfinished-work list (its GitHub Issues equivalent here = this repo's own durable TODO
# tracker, the spec/plan TODO tables -- CLAUDE.md already treats these as the canonical
# "二重トラック" alongside the live TaskList tool, which is session-scoped and unreachable
# from this headless script), project purpose (README head), and continuity with recent
# output (past 7 days' devlog cards, so today's card does not repeat the same angle).
# All git/grep steps go through a temp FILE, never a live pipe from `git log -p` straight
# into grep -- piping git's multi-KB stdout through 3 chained grep stages in this shell
# silently returned 0 matches on a diff that demonstrably had 84 (verified empirically,
# 2026-07-17); writing to a temp file first and grepping the file gave the correct count
# every time. Same defensive pattern as TRANSCRIPT_TMP above.
# ============================================================================
TODO_DIFF_TMP="$(mktemp)"
git -C "$HOME/anicca-project" log --since=midnight -p --no-color -- 'docs/superpowers/specs/*.md' 'docs/superpowers/plans/*.md' >"$TODO_DIFF_TMP" 2>/dev/null
TODO_DIFF="$(grep -E '^[+-]' "$TODO_DIFF_TMP" 2>/dev/null | grep -vE '^(\+\+\+|---) ' | grep -E '\[[ xX]\]' | sort -u || true)"
rm -f "$TODO_DIFF_TMP"
TODO_COUNT=0
if [ -n "$TODO_DIFF" ]; then
  { echo "=== TODO TABLE CHANGES TODAY (docs/superpowers/specs+plans, unfinished-work context) ==="; printf '%s\n\n' "$TODO_DIFF"; } >>"$MATERIAL_FILE"
  TODO_COUNT=$(printf '%s\n' "$TODO_DIFF" | grep -c . || true)
fi

# Currently-outstanding TODO rows (not diffed -- the CURRENT state of unfinished work,
# devlog-ai's "open GitHub Issues" equivalent), capped so one huge spec table cannot crowd
# out the rest of the material.
OPEN_TODO_TMP="$(mktemp)"
grep -RhE '\[ \]' "$HOME/anicca-project/docs/superpowers/specs/" "$HOME/anicca-project/docs/superpowers/plans/" 2>/dev/null | head -30 >"$OPEN_TODO_TMP" || true
if [ -s "$OPEN_TODO_TMP" ]; then
  { echo "=== CURRENTLY OPEN TODOs (specs+plans, capped 30 rows) ==="; cat "$OPEN_TODO_TMP"; echo; } >>"$MATERIAL_FILE"
fi
rm -f "$OPEN_TODO_TMP"

# Project purpose context (mcp-commit-story's README injection).
README_LINES=0
if [ -f "$HOME/profitable-claude/README.md" ]; then
  { echo "=== PROJECT CONTEXT: profitable-claude/README.md (head) ==="; head -30 "$HOME/profitable-claude/README.md"; echo; } >>"$MATERIAL_FILE"
  README_LINES=$(head -30 "$HOME/profitable-claude/README.md" | wc -l | tr -d ' ')
fi

# Continuity with the past 7 days' cards (so today's card does not repeat the same angle).
PAST_CARDS_TMP="$(mktemp)"
find "$QUEUE_DIR" "$TOPICS_DIR/done" "$TOPICS_DIR/in-progress" -maxdepth 1 -type f -name '*-devlog.md' -mtime -7 2>/dev/null | sort | while IFS= read -r f; do
  ANGLE_LINE="$(grep -m1 '^angle:' "$f" 2>/dev/null)"
  printf '%s: %s\n' "$(basename "$f")" "$ANGLE_LINE"
done >"$PAST_CARDS_TMP"
PAST_CARD_COUNT=$(wc -l <"$PAST_CARDS_TMP" | tr -d ' ')
if [ "$PAST_CARD_COUNT" -gt 0 ]; then
  { echo "=== PAST 7 DAYS' DEVLOG CARDS (continuity -- do not repeat the same angle) ==="; cat "$PAST_CARDS_TMP"; echo; } >>"$MATERIAL_FILE"
fi
rm -f "$PAST_CARDS_TMP"

# Overall input cap (#55b, spec §7.6 row + team-lead instruction: "超過は git log 側から削
# る"): a single unusually busy day (many repos, many commits) could otherwise blow the whole
# material past what a single model judge call should reasonably carry. MATERIAL_FILE at this
# point holds everything EXCEPT git log (docs, transcript, TODO diff/open, README, past
# cards -- each already self-capped: transcript 1500, open-TODO 30, README 30). Git log is
# prepended last, trimmed to whatever budget remains under the 3000-line total -- it is the
# least essential section now that the #55b context injections exist, and usually the
# largest, so it is what gets cut, never the newer context.
OTHER_LINES=$(wc -l <"$MATERIAL_FILE" | tr -d ' ')
GITLOG_LINES=$(wc -l <"$GITLOG_TMP" | tr -d ' ')
GIT_LOG_BUDGET=$((3000 - OTHER_LINES))
[ "$GIT_LOG_BUDGET" -lt 0 ] && GIT_LOG_BUDGET=0
if [ "$GITLOG_LINES" -gt "$GIT_LOG_BUDGET" ]; then
  head -"$GIT_LOG_BUDGET" "$GITLOG_TMP" >"${GITLOG_TMP}.capped"
  printf '\n[... git log truncated: %s total lines collected across repos, capped to %s to keep the overall material under 3000 lines ...]\n' "$GITLOG_LINES" "$GIT_LOG_BUDGET" >>"${GITLOG_TMP}.capped"
  mv "${GITLOG_TMP}.capped" "$GITLOG_TMP"
fi
cat "$GITLOG_TMP" "$MATERIAL_FILE" >"${MATERIAL_FILE}.withgitlog"
mv "${MATERIAL_FILE}.withgitlog" "$MATERIAL_FILE"
rm -f "$GITLOG_TMP"
MATERIAL_TOTAL_LINES=$(wc -l <"$MATERIAL_FILE" | tr -d ' ')

echo "[collect] commits=$COMMIT_COUNT docs=$DOC_COUNT transcript_lines=$TRANSCRIPT_LINES todo_diff_rows=$TODO_COUNT readme_lines=$README_LINES past_cards=$PAST_CARD_COUNT material_total_lines=$MATERIAL_TOTAL_LINES material=$MATERIAL_FILE" >>"$LOG"

if [ "$COLLECT_ONLY" -eq 1 ]; then
  echo "MATERIAL_FILE=$MATERIAL_FILE"
  echo "commits=$COMMIT_COUNT docs=$DOC_COUNT transcript_lines=$TRANSCRIPT_LINES todo_diff_rows=$TODO_COUNT readme_lines=$README_LINES past_cards=$PAST_CARD_COUNT material_total_lines=$MATERIAL_TOTAL_LINES"
  head -20 "$MATERIAL_FILE"
  exit 0
fi

if [ "$COMMIT_COUNT" -eq 0 ] && [ "$DOC_COUNT" -eq 0 ] && [ "$TRANSCRIPT_LINES" -eq 0 ]; then
  echo "NO CARD (no material)"
  echo "=== make-diary-digest NO CARD (no material) $(date '+%F %T %Z') ===" >>"$LOG"
  rm -f "$MATERIAL_FILE"
  exit 0
fi

# ============================================================================
# STEP 2 (lesson extraction, judgment through the single provider-neutral model boundary).
# ============================================================================
MATERIAL_CONTENT="$(cat "$MATERIAL_FILE")"
# #55b (docs/loop-engineering/53-devlog-to-article-pipelines-gh-research.md 「具体反映」節):
# mcp-commit-story の実測結論を反映 — 売れる型の序列は「失敗談型 > 教訓抽出型 > 進捗報告型」。
# 症状→誤った本能→正しい手→一般法則、の抽出フォーマット自体は既に失敗談型と一致しているので
# 変えない。変えるのは「複数の候補があるとき、どれを選ぶか」の優先順位付けの指示。
PROMPT="以下は今日の開発ログ(git log)・TODO表の変化と積み残し・README(プロジェクトの目的)・
過去7日分のカードの見出し(重複回避用)・更新されたdocs・session transcript の一部(人間発話のみ)。
これは**報告ではなく教訓抽出**のタスク: 症状→誤った本能→正しい手→一般法則、の形式で、
他の開発者/AI運用者が持ち帰れる一般化された学びを抽出しろ。特定の固有名詞(プロジェクト名や
ファイル名)を残してもよいが、必ず一般法則の形で締めること。

★優先順位★: 複数の候補教訓がある場合、**失敗談として書けるものを最優先**しろ——何を間違え、
どの瞬間に気づき、どう直したか。時系列のドラマ(最初はこう思っていた→実は違った→こう発覚した
→こう直した)があるものが最上。**進捗報告(単に「〜をした」「〜を実装した」という時系列ドラマの
無い作業列挙)は書くな**——材料の中に失敗談として書けるものが1つも無く、進捗報告しか書けない
場合は、カード本文を書かず NOTHING とだけ出力しろ(進捗報告カードを出すくらいなら何も出さない
方がよい)。過去7日分のカード見出しと同じアングルを繰り返すな(見出しが与えられている場合)。
TODO表の積み残しは背景文脈として使ってよいが、それ自体を教訓として出力するな。

読者が持ち帰れる一般化された学びが1つ以上見つかった場合のみ、以下の形式で出力しろ:
1行目: ANGLE: <一般化された学びの1行要約>
2行目: 空行
3行目以降: カード本文(markdown箇条書き、症状→誤った本能→正しい手→一般法則の形式、1-3個の教訓)

一般化された学びが1つも無い(単なる作業ログ・雑談のみ)場合は、他に何も書かず NOTHING とだけ出力しろ。

=== 材料 ===
$MATERIAL_CONTENT"

run_model_judge() {
  printf '%s' "$PROMPT" | "$MODEL_RUNNER" judge --prompt-file -
}

LESSON_RAW="$(run_model_judge 2>>"$LOG")"
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "[extract] model judge failed rc=$RC" >>"$LOG"
  echo "NO CARD (model judge failed rc=$RC)"
  rm -f "$MATERIAL_FILE"
  exit 0
fi

if [ -z "$LESSON_RAW" ] || printf '%s' "$LESSON_RAW" | grep -q '^NOTHING$'; then
  echo "NO CARD (no lesson extracted today)"
  echo "=== make-diary-digest NO CARD (no lesson) $(date '+%F %T %Z') ===" >>"$LOG"
  rm -f "$MATERIAL_FILE"
  exit 0
fi

ANGLE="$(printf '%s\n' "$LESSON_RAW" | head -1 | sed -E 's/^ANGLE:[[:space:]]*//')"
# awk (not sed) to strip only LEADING blank lines after the ANGLE line: macOS ships BSD sed,
# whose brace-nesting for this differs from GNU sed and silently mis-parses.
BODY="$(printf '%s\n' "$LESSON_RAW" | tail -n +2 | awk 'BEGIN{skip=1} skip && /^[[:space:]]*$/{next} {skip=0; print}')"
[ -z "$ANGLE" ] && ANGLE="今日の開発ログから抽出した教訓"
[ -z "$BODY" ] && BODY="$LESSON_RAW"

# ============================================================================
# STEP 3 (redaction gate, mandatory before ANY write) — applied to the extracted output,
# not the raw material, per spec: this is what actually lands in a committed queue card.
# ============================================================================
if ! printf '%s\n%s' "$ANGLE" "$BODY" | redaction_scan 2>>"$LOG"; then
  echo "REDACTION FAIL: extracted lesson contained a secret-shaped string, card NOT written. See $LOG."
  echo "=== make-diary-digest REDACTION FAIL $(date '+%F %T %Z') ===" >>"$LOG"
  rm -f "$MATERIAL_FILE"
  exit 1
fi

# ============================================================================
# STEP 4 (card output) — same frontmatter shape as the other queue/ cards.
# ============================================================================
{
  echo "---"
  echo "lane: A"
  printf 'created: "%s"\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "voice: recit"
  echo "sources:"
  if [ "${#DOC_PATHS[@]}" -gt 0 ]; then
    for p in "${DOC_PATHS[@]}"; do
      echo "  - $p"
    done
  else
    echo "  - git log ($(date +%F), see article-diary-digest.log)"
  fi
  printf 'angle: %s\n' "$ANGLE"
  echo "---"
  echo
  printf '%s\n' "$BODY"
} >"$CARD_PATH"

echo "CARD WRITTEN: $CARD_PATH"
echo "=== make-diary-digest CARD WRITTEN $CARD_PATH $(date '+%F %T %Z') ===" >>"$LOG"
rm -f "$MATERIAL_FILE"
exit 0
