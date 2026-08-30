#!/usr/bin/env bash
# reader-testing-gate.sh — READER-TESTING gate (spec docs/loop-engineering/47-writer-loop-quality-and-
# self-improvement.md §4/§7, P0-3 copy+tweak from github.com/anthropics/skills doc-coauthoring/: "Test the
# document with a fresh model (no context bleed) ... catches blind spots"). Two-call design, same shape
# as identity-gate.sh/rubric-judge.sh but split across TWO independent judge invocations so the second
# (answering) call never sees the first (question-generation) call's reasoning -- only the article body and
# the plain question list, exactly what a genuine first-time reader would have:
#   (1) STORM-persona question generation -- reads the draft AND the SKILL.md 読者persona3種 framing to
#       imagine 3 distinct first-time readers, then asks: what would each of them actually want answered to
#       understand this piece? 5-10 questions.
#   (2) fresh, context-zero judge -- given ONLY the article text + the question list (no persona reasoning,
#       no spec, no conversation history), answers each question using the article alone. Any question it
#       cannot confidently answer from the article is a blind spot the reader would hit.
# Usage: reader-testing-gate.sh <article.md> [--lang ja|en]
# stdout: one JSON line {"verdict":"PASS|FAIL","questions":[...],"unanswered_questions":[...]}
# exit 0 only on PASS.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_RUNNER="${ARTICLE_MODEL_RUNNER:-${ARTICLE_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)}/runtime/model-runner.sh}"
READER_STDOUT_SCHEMA_VERSION=2

MD=""; LANG_A="ja"; QUESTIONS_FILE=""
POSITIONAL=()
while [ $# -gt 0 ]; do case "$1" in
  --lang) LANG_A="$2"; shift 2;;
  --markdown-file) MD="$2"; shift 2;;   # accepted for consistency with the other gates
  --questions-file) QUESTIONS_FILE="$2"; shift 2;;
  *) POSITIONAL+=("$1"); shift;;
esac; done
[ -z "$MD" ] && [ ${#POSITIONAL[@]} -gt 0 ] && MD="${POSITIONAL[0]}"
[ -f "$MD" ] || { echo "FATAL: usage: reader-testing-gate.sh <article.md> [--lang ja|en]" >&2; exit 2; }

# The stable question cache bounds WHAT is tested; this persistent controller bounds HOW
# MANY evaluations one run/lang may spend and makes wrapper resumes idempotent.
GATE_CONTROL="$SCRIPT_DIR/gate-attempt-control.py"
GATE_CONTROL_ACTIVE=0
GATE_ATTEMPT=0
GATE_OUTPUT_FILE=""
if [ -n "${ARTICLE_RUN_DIR:-}" ]; then
  BEGIN_JSON=$(python3 "$GATE_CONTROL" begin --run-dir "$ARTICLE_RUN_DIR" --gate reader-testing-gate --lang "$LANG_A" --markdown-file "$MD") || exit 3
  BEGIN_ACTION=$(printf '%s' "$BEGIN_JSON" | jq -r '.action')
  case "$BEGIN_ACTION" in
    skip-pass)
      printf '%s\n' "$BEGIN_JSON" | jq -c '.payload'
      exit 0
      ;;
    skip-advisory)
      PAYLOAD=$(printf '%s' "$BEGIN_JSON" | jq -c '.payload // empty')
      if [ -n "$PAYLOAD" ]; then printf '%s\n' "$PAYLOAD"; else printf '%s\n' '{"verdict":"STOP_SPENDING","reason":"terminal gate artifact"}'; fi
      exit 75
      ;;
    skip-revision-required)
      PAYLOAD=$(printf '%s' "$BEGIN_JSON" | jq -c '.payload // empty')
      if [ -n "$PAYLOAD" ]; then printf '%s\n' "$PAYLOAD"; else printf '%s\n' '{"verdict":"REVISION_REQUIRED","reason":"same article hash already failed reader testing"}'; fi
      exit 75
      ;;
    run)
      GATE_ATTEMPT=$(printf '%s' "$BEGIN_JSON" | jq -r '.attempt')
      GATE_OUTPUT_FILE=$(mktemp /tmp/article-reader-output.XXXXXX) || exit 3
      GATE_CONTROL_ACTIVE=1
      ;;
    *) echo "FATAL: invalid gate control action: $BEGIN_ACTION" >&2; exit 3 ;;
  esac
fi

finish_gate_attempt() {
  rc=$?
  trap - EXIT
  if [ "$GATE_CONTROL_ACTIVE" -eq 1 ]; then
    finish_rc=0
    python3 "$GATE_CONTROL" finish --run-dir "$ARTICLE_RUN_DIR" --gate reader-testing-gate --lang "$LANG_A" \
      --attempt "$GATE_ATTEMPT" --exit-code "$rc" --output-file "$GATE_OUTPUT_FILE" \
      --markdown-file "$MD" >/dev/null 2>&1 || finish_rc=$?
    rm -f "$GATE_OUTPUT_FILE"
    if [ "$finish_rc" -ne 0 ]; then
      exit 3
    fi
  fi
  exit "$rc"
}
trap finish_gate_attempt EXIT

if [ -n "${ARTICLE_GATES_LOG:-}" ]; then
  GATES_LOG="$ARTICLE_GATES_LOG"
elif [ -n "${ARTICLE_RUN_DIR:-}" ]; then
  GATES_LOG="$ARTICLE_RUN_DIR/gates/article-gates.log"
else
  GATES_LOG="${ARTICLE_STATE_DIR:-$HOME/.local/state/life-manager/writer}/logs/article-gates.log"
fi
log_gate_verdict() {
  mkdir -p "$(dirname "$GATES_LOG")" 2>/dev/null || return 0
  printf '%s script=reader-testing-gate.sh md=%s lang=%s verdict=%s\n' \
    "$(date '+%Y-%m-%d %H:%M:%S')" "$MD" "$LANG_A" "$1" >>"$GATES_LOG" 2>/dev/null || true
}

BODY="$(cat "$MD")"

# ---- (1) QUESTION GENERATION -- STORM 3-persona (SKILL.md 読者persona3種) ----
# A bounded refinement cycle must test a stable target. When --questions-file is provided,
# generate and persist the set once, then reuse it byte-for-byte on every revised draft.
Q_PROMPT="You are generating a reader-testing question set for a publishable article (spec
docs/loop-engineering/47-writer-loop-quality-and-self-improvement.md, P0-3 copy of
github.com/anthropics/skills doc-coauthoring/ Reader Testing, combined with the STORM
persona_generator.py method: stanford-oval/storm).

Read the article below. Imagine THREE distinct first-time readers who might plausibly pick this
article up (e.g. a total newcomer to the topic, someone deciding whether to actually use/adopt
what the article describes, someone who already knows the basics but wants to be convinced with
real numbers -- the actual three depend on this article's specific topic, do not force these exact
three if the topic implies different ones).

For each persona, ask yourself: what would THIS reader need answered to genuinely understand this
piece and judge whether it was worth their time? Then produce ONE combined list of 5 to 10
concrete questions (not questions about the writing quality itself -- questions about the SUBJECT
MATTER a first-time reader would actually have: what is this thing, why does it matter, what did
it actually do/cost/prove, what is the catch).

Output the FINAL LINE as pure JSON exactly, with no other keys and no commentary after it:
{\"questions\":[\"<question 1>\", \"<question 2>\", ...]}

=== ARTICLE (lang=$LANG_A) ===
$BODY"

validate_questions_json() {
  python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    questions = data.get("questions") if isinstance(data, dict) else None
    valid = (
        isinstance(questions, list)
        and 5 <= len(questions) <= 10
        and all(isinstance(q, str) and q.strip() for q in questions)
    )
    if not valid:
        raise ValueError("questions must contain 5-10 non-empty strings")
    print(json.dumps({"questions": questions}, ensure_ascii=False, separators=(",", ":")))
except Exception as exc:
    print(str(exc), file=sys.stderr)
    raise SystemExit(1)
'
}

if [ -n "$QUESTIONS_FILE" ] && [ -e "$QUESTIONS_FILE" ]; then
  Q_JSON=$(validate_questions_json <"$QUESTIONS_FILE" 2>/dev/null)
  if [ -z "$Q_JSON" ]; then
    log_gate_verdict "FATAL:invalid-questions-cache"
    echo "FATAL: existing --questions-file is invalid; refusing to overwrite: $QUESTIONS_FILE" >&2
    exit 3
  fi
else
# Judge broker routing must survive agent subshells that drop env vars
# (observed 2026-07-25): the markdown lives in the run dir, so derive
# ARTICLE_RUN_DIR from it whenever the caller failed to pass one.
if [ -z "${ARTICLE_RUN_DIR:-}" ] && [ -f "$MD" ]; then
  export ARTICLE_RUN_DIR="$(cd "$(dirname "$MD")" && pwd)"
fi
  Q_OUT=$(printf '%s' "$Q_PROMPT" | "$MODEL_RUNNER" judge --prompt-file - 2>/dev/null)
  Q_RAW=$(printf '%s\n' "$Q_OUT" | grep -o '{"questions".*}' | tail -1)
  if [ -z "$Q_RAW" ]; then
    log_gate_verdict "FATAL:no-questions-json"
    echo "FATAL: question-generation call returned no JSON" >&2
    printf '%s\n' "$Q_OUT" | tail -5 >&2
    exit 3
  fi
  Q_JSON=$(printf '%s' "$Q_RAW" | validate_questions_json 2>/dev/null)
  if [ -z "$Q_JSON" ]; then
    log_gate_verdict "FATAL:invalid-question-list"
    echo "FATAL: question-generation JSON must contain 5-10 non-empty questions" >&2
    exit 3
  fi
  if [ -n "$QUESTIONS_FILE" ]; then
    QUESTIONS_DIR=$(dirname "$QUESTIONS_FILE")
    mkdir -p "$QUESTIONS_DIR" || {
      log_gate_verdict "FATAL:questions-cache-mkdir"
      echo "FATAL: cannot create questions cache directory: $QUESTIONS_DIR" >&2
      exit 3
    }
    QUESTIONS_TMP=$(mktemp "${QUESTIONS_FILE}.tmp.XXXXXX") || {
      log_gate_verdict "FATAL:questions-cache-temp"
      echo "FATAL: cannot create temporary questions cache" >&2
      exit 3
    }
    if ! printf '%s\n' "$Q_JSON" >"$QUESTIONS_TMP" || ! mv "$QUESTIONS_TMP" "$QUESTIONS_FILE"; then
      log_gate_verdict "FATAL:questions-cache-write"
      echo "FATAL: cannot atomically persist questions cache: $QUESTIONS_FILE" >&2
      exit 3
    fi
  fi
fi

QUESTIONS_TEXT=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
qs = d.get('questions', [])
for i, q in enumerate(qs, 1):
    print(f'{i}. {q}')
" "$Q_JSON" 2>/dev/null)
if [ -z "$QUESTIONS_TEXT" ]; then
  log_gate_verdict "FATAL:empty-question-list"
  echo "FATAL: question-generation JSON had no usable questions array" >&2
  exit 3
fi

# ---- (2) FRESH, CONTEXT-ZERO JUDGE -- article text + question list ONLY, no persona reasoning ----
# Deliberately a brand-new judge call: it never receives Q_PROMPT, this script's own reasoning,
# or any conversation history -- only the article body and the plain numbered question list below,
# exactly what a genuine first-time reader arriving at the published piece would have.
A_PROMPT="You are a first-time reader with ZERO other context: you have never seen any spec,
conversation, persona notes, or background material -- only what is printed below.

Below is an ARTICLE and a QUESTION LIST that a first-time reader of this article would want
answered. For EACH question, read the article and decide: can a reader confidently answer this
question using ONLY the article text below (not outside knowledge, not guessing)? If yes, note
briefly how/where the article answers it. If no, that question is a blind spot.

=== ARTICLE (lang=$LANG_A) ===
$BODY

=== QUESTIONS ===
$QUESTIONS_TEXT

Output the FINAL LINE as pure JSON exactly:
{\"unanswered_questions\":[\"<question that could NOT be answered from the article alone>\", ...]}
unanswered_questions is empty ONLY if every question above was genuinely answerable from the
article text alone."

A_OUT=$(printf '%s' "$A_PROMPT" | "$MODEL_RUNNER" judge --prompt-file - 2>/dev/null)
A_JSON=$(printf '%s\n' "$A_OUT" | grep -o '{"unanswered_questions".*}' | tail -1)
if [ -z "$A_JSON" ]; then
  log_gate_verdict "FATAL:no-answer-json"
  echo "FATAL: reader-judge call returned no JSON" >&2
  printf '%s\n' "$A_OUT" | tail -5 >&2
  exit 3
fi

ARTICLE_HASH=$(shasum -a 256 "$MD" | awk '{print $1}')
MERGED_JSON=$(python3 -c "
import json, sys
q = json.loads(sys.argv[1]).get('questions', [])
a = json.loads(sys.argv[2])
unanswered = a.get('unanswered_questions', [])
verdict = 'PASS' if len(unanswered) == 0 else 'FAIL'
payload = {
    'verdict': verdict,
    'questions': q,
    'unanswered_questions': unanswered,
}
# Keep the historical top-level shape for callers while making stdout itself
# a self-describing terminal. An autonomous caller that redirects or copies
# stdout over the canonical terminal path can no longer erase the article
# binding required by quality_self_heal.py.
terminal = {
    **payload,
    'gate': 'reader-testing-gate',
    'lang': sys.argv[4],
    'status': 'pass' if verdict == 'PASS' else 'fail',
    'attempts': int(sys.argv[5]),
    'article_sha256': sys.argv[3],
    'payload': payload,
}
print(json.dumps(terminal, separators=(',', ':'), ensure_ascii=False))
" "$Q_JSON" "$A_JSON" "$ARTICLE_HASH" "$LANG_A" "${GATE_ATTEMPT:-0}" 2>/dev/null)
if [ -z "$MERGED_JSON" ]; then
  log_gate_verdict "FATAL:merge-failed"
  echo "FATAL: could not merge question/answer JSON" >&2
  exit 3
fi

[ "$GATE_CONTROL_ACTIVE" -eq 0 ] || printf '%s\n' "$MERGED_JSON" >"$GATE_OUTPUT_FILE"
echo "$MERGED_JSON"
VERDICT=$(printf '%s' "$MERGED_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['verdict'])" 2>/dev/null)
log_gate_verdict "${VERDICT:-UNKNOWN}"
[ "$VERDICT" = "PASS" ]
