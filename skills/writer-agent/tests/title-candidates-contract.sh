#!/usr/bin/env bash
# Contract for the title candidate ledger (spec 47 section 19).
#
# The fixtures are the real 2026-07-26 incident: the loop shipped a
# measurement-report headline and discarded three stronger candidates with
# reasons that named the rulebook rather than the reader. Those exact reasons
# must now be refused, because they are what made the defect invisible.
set -uo pipefail

SCRIPT="${ARTICLE_SKILL_DIR:-$HOME/profitable-claude/skills/writer-agent}/scripts/title_candidates.py"
PY=/opt/homebrew/bin/python3
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PASS=0
FAIL=0

check() {
  local name="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    PASS=$((PASS + 1))
    printf 'ok   %s\n' "$name"
  else
    FAIL=$((FAIL + 1))
    printf 'FAIL %s (expected rc=%s got rc=%s)\n' "$name" "$expected" "$actual"
  fi
}

run() { "$PY" "$SCRIPT" validate --json "$1" >/dev/null 2>&1; echo $?; }

# 1. The incident as it actually happened: rulebook reasons, no cited lines.
cat > "$TMP/incident.json" <<'JSON'
{"chosen": {"title": "コーディング補助の返答を192回比べたら、日本語は28%減、英語は3%増だった",
            "why": "実測した数字を見出しに出しているから"},
 "rejected": [
  {"title": "バイブコーディングの本質は速度ではない", "reason": "否定形で始まると読者が敵になる。診断型フックの方が強い"},
  {"title": "The major sufferer becomes the major builder", "reason": "抽象語だけで殴っていて手が止まらない"},
  {"title": "24年間ダメだった僕が", "reason": "self-as-subject。skill が明示的に禁止してる軸"},
  {"title": "測って分かった日英の差", "reason": "型に合わない"}]}
JSON
check "the 2026-07-26 rejections are refused" 3 "$(run "$TMP/incident.json")"

# 2. Reader-side reasons but no rule cited: blame cannot land on a line.
cat > "$TMP/nocite.json" <<'JSON'
{"chosen": {"title": "測定を3回やり直して分かったこと", "why": "見知らぬ人でも読む理由が1行で分かるから"},
 "rejected": [
  {"title": "A", "reason": "知らない語が2つあって主語が分解できない"},
  {"title": "B", "reason": "読んでも何が得られるか分からない"},
  {"title": "C", "reason": "クリックする理由がどこにも無い"},
  {"title": "D", "reason": "約束している内容が本文と一致しない"}]}
JSON
check "reader-side reason without a cited line is refused" 3 "$(run "$TMP/nocite.json")"

# 3. Fewer than five candidates: the gate has no counterfactuals to score.
cat > "$TMP/thin.json" <<'JSON'
{"chosen": {"title": "見出しの候補が足りない例", "why": "見知らぬ人が続きを読む理由を言えるから"},
 "rejected": [
  {"title": "A", "reason": "知らない語が2つあって主語が分解できない", "cited_rule": "reference/title-best-practices.md:80"},
  {"title": "B", "reason": "読んでも何が得られるか分からない", "cited_rule": "SKILL.md:132"}]}
JSON
check "fewer than five candidates is refused" 3 "$(run "$TMP/thin.json")"

# 4. A well-formed ledger: reader-side reasons, every rejection citing a line.
cat > "$TMP/good.json" <<'JSON'
{"chosen": {"title": "一人前のエンジニアなら、PRでコメントをもらうな",
            "why": "読者が当たり前だと思っている習慣を名指しで壊しているから"},
 "rejected": [
  {"title": "PRレビューの効率化について", "reason": "何が分かるのか一切約束していない",
   "cited_rule": "reference/title-best-practices.md:81"},
  {"title": "Mech Requester の設計", "reason": "知らない語が2つあり主語が分解できない",
   "cited_rule": "reference/title-best-practices.md:80"},
  {"title": "PRを192回比べたら指摘は28%減った", "reason": "何を測ったかしか言っておらず読者の何が変わるか言っていない",
   "cited_rule": "SKILL.md:132"},
  {"title": "PRレビュー徹底解説", "reason": "説明が存在すると言っているだけで情報量がゼロ",
   "cited_rule": "reference/title-best-practices.md:81"}]}
JSON
check "a well-formed ledger is accepted" 0 "$(run "$TMP/good.json")"

# 5. record writes the ledger where the trainer looks for it.
"$PY" "$SCRIPT" record --json "$TMP/good.json" --run-dir "$TMP/run" --lang ja >/dev/null 2>&1
# Under gates/, because that is where score-latest-run.sh looks. A ledger
# written anywhere else is a ledger nobody reads.
if [ -f "$TMP/run/gates/title-candidates-ja.json" ]; then
  PASS=$((PASS + 1)); printf 'ok   record writes gates/title-candidates-ja.json\n'
else
  FAIL=$((FAIL + 1)); printf 'FAIL record did not write gates/title-candidates-ja.json\n'
fi

printf '\n%s passed, %s failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
