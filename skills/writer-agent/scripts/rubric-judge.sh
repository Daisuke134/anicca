#!/usr/bin/env bash
# rubric-judge.sh — RUBRIC gate (spec docs/loop-engineering/47-writer-loop-quality-and-self-improvement.md
# §3 P0-2): EQ-bench (github.com/EQ-bench/creative-writing-bench) + gpt-newspaper
# (github.com/rotemweiss57/gpt-newspaper) style judge for reader-first writing quality. Copy+tweak:
#   - EQ-bench's "analyze THEN score" order (the judge writes its reasoning before committing to a number)
#   - EQ-bench's separate NEGATIVE-CRITERIA deduction (Meandering/Tell-Don't-Show/etc in their rubric,
#     jargon-density/内輪文脈/構成が時系列/読者不在 in ours) instead of folding penalties into one blended score
#   - gpt-newspaper's revise-until-empty termination condition: SKILL.md's process section says to loop
#     revise->re-gate until "improvements" is empty or 3 attempts are exhausted, never fewer gates for speed
# Usage: rubric-judge.sh <article.md> [--lang ja|en] [--threshold 70]
# stdout: one JSON line
#   {"verdict":"PASS|FAIL","scores":{"lead":N,"one_reader":N,"promise":N,"why_pay":N,"jargon_defined":N},
#    "positive_total":N,"deductions":[{"category":"...","detail":"..."}],"final_score":N,
#    "improvements":["..."]}
# exit 0 only on PASS.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_RUNNER="${ARTICLE_MODEL_RUNNER:-${ARTICLE_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)}/runtime/model-runner.sh}"

MD=""; LANG_A="ja"; TH=70; LANE=""
POSITIONAL=()
while [ $# -gt 0 ]; do case "$1" in
  --lang) LANG_A="$2"; shift 2;;
  --threshold) TH="$2"; shift 2;;
  --lane) LANE="$2"; shift 2;;
  --markdown-file) MD="$2"; shift 2;;  # accepted for consistency with the other gates
  *) POSITIONAL+=("$1"); shift;;
esac; done
[ -z "$MD" ] && [ ${#POSITIONAL[@]} -gt 0 ] && MD="${POSITIONAL[0]}"
[ -f "$MD" ] || { echo "FATAL: usage: rubric-judge.sh <article.md> [--lang ja|en] [--threshold 70] [--lane a|b]" >&2; exit 2; }

# Persist the policy boundary in the gate itself. The agent may revise the draft, but it
# cannot spend a fourth evaluation or rerun a terminal gate after a wrapper resume.
GATE_CONTROL="$SCRIPT_DIR/gate-attempt-control.py"
GATE_CONTROL_ACTIVE=0
GATE_ATTEMPT=0
GATE_OUTPUT_FILE=""
if [ -n "${ARTICLE_RUN_DIR:-}" ]; then
  BEGIN_JSON=$(python3 "$GATE_CONTROL" begin --run-dir "$ARTICLE_RUN_DIR" --gate rubric-judge --lang "$LANG_A" --markdown-file "$MD") || exit 3
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
    run)
      GATE_ATTEMPT=$(printf '%s' "$BEGIN_JSON" | jq -r '.attempt')
      GATE_OUTPUT_FILE=$(mktemp /tmp/article-rubric-output.XXXXXX) || exit 3
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
    python3 "$GATE_CONTROL" finish --run-dir "$ARTICLE_RUN_DIR" --gate rubric-judge --lang "$LANG_A" \
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

# SKILL.md rule 7 (lane A / rubric-judge known gap, 2026-07-20/21): self_as_subject and
# chronological_diary are lane-B-only axes (Dais's SUBJECT=EXPLAINER ruling, line 48) that
# structurally cannot pass a compliant lane A récit (diary framing + investigation order are
# the lane A voice by design, see lane A rule 2). If --lane wasn't given explicitly, read it
# off the draft's own frontmatter (`lane: A` / `lane: B`); default to lane B (strict) if absent.
if [ -z "$LANE" ]; then
  FM_LANE=$(sed -n '2,20p' "$MD" | grep -m1 -E '^lane: *[AaBb]' | grep -oE '[AaBb]$')
  LANE=$(printf '%s' "${FM_LANE:-b}" | tr '[:upper:]' '[:lower:]')
fi

if [ -n "${ARTICLE_GATES_LOG:-}" ]; then
  GATES_LOG="$ARTICLE_GATES_LOG"
elif [ -n "${ARTICLE_RUN_DIR:-}" ]; then
  GATES_LOG="$ARTICLE_RUN_DIR/gates/article-gates.log"
else
  GATES_LOG="${ARTICLE_STATE_DIR:-$HOME/.local/state/life-manager/writer}/logs/article-gates.log"
fi
log_gate_verdict() {
  mkdir -p "$(dirname "$GATES_LOG")" 2>/dev/null || return 0
  printf '%s script=rubric-judge.sh md=%s lang=%s verdict=%s\n' \
    "$(date '+%Y-%m-%d %H:%M:%S')" "$MD" "$LANG_A" "$1" >>"$GATES_LOG" 2>/dev/null || true
}

PROMPT="You are a fresh, EQ-bench-style writing-quality judge. ANALYZE FIRST, THEN SCORE (write your
reasoning for each dimension before committing to its number -- do not jump straight to numbers).

You are grading whether this article was written for a genuine, specific reader (per William Zinsser:
'write for one reader, not an audience') or is generic AI-slop that could be about anything for anyone.

=== POSITIVE AXES (0-20 each, 100 total) ===
1. LEAD (does the lead make the reader want to read the 2nd sentence, and the 2nd want the 3rd? A lead that
   states a topic instead of creating a specific hook scores low)
2. ONE READER (is there ONE identifiable reader this piece is written for -- can you name who they are and
   what they already know? A piece addressed to a vague 'anyone interested in X' scores low)
3. PROMISE UP FRONT (does the opening state, in plain language, what the reader will understand/be able to
   do after reading -- not framed as 'this article will explain' but simply delivering the promise)
4. WHY-PAY / WHY-CARE (does the piece make explicit, early, why this specific reader should spend their
   time or money on it -- the stakes, not just the facts)
5. JARGON DEFINED ON FIRST USE (every technical term/acronym/proper noun the target reader would not already
   know is defined in one plain clause at first use -- a katakana transliteration of an English term is NOT
   a definition; score low if jargon appears undefined, especially in the title or first paragraph)

=== NEGATIVE CRITERIA (separate deductions, NOT blended into the positive score above -- report each hit
even if the positive score is high; EQ-bench keeps these separate for exactly this reason: a fluent piece
can still be structurally broken) ===
- JARGON DENSITY: count of undefined jargon terms across the whole piece (not just first use) -- report the
  actual count and quote 2-3 examples
- TITLE JARGON (category: title_jargon): Judge the HEADLINE ALONE against a stranger who does NOT yet know
  they are the target reader. Penalize if the title contains a vendor/product proper noun, an acronym, or
  a technical term that is not the single irreducible subject -- EVEN IF the body later defines it, because
  the title is read before the body. The title's job is to promise the FINDING in plain language, naming the
  function/category (what the thing does or is), not the vendor. A proper noun is allowed only if it is the
  one irreducible subject AND is preceded by its plain-language function/category.
  Few-shot examples span DIFFERENT domains on purpose -- learn the PATTERN (function/finding first,
  vendor/proper-noun secondary), not any one topic. This rule applies to every writing form: article
  headline, X-post hook, ebook title.
  (agent-marketplace) BAD 'Base上のVirtuals ACP、検収役はハンコで5%取れた'
                      GOOD '元手ゼロのAIは稼げるか。エージェント向け取引所のVirtuals ACPを試してみた'
  (dev-tool review)   BAD 'DrizzleのRLSとpgvectorでRAG検索を実装してみた'
                      GOOD '型安全なDBだけでAI検索は作れるか。話題のDrizzleで試した'
  (narrative/consumer) BAD 'CESでNVIDIAのJetson Thorを触ってきた'
                      GOOD 'ロボットの脳が手のひらサイズに。最新の小型AIチップを見てきた'
  (X-post hook)       BAD 'x402とERC-8004でエージェント決済を検証した'
                      GOOD 'AIが人間なしで請求書を払えるか、実際に送金させてみた'
  In every GOOD case the finding/function leads in plain words; the proper noun, if kept at all, comes
  after its plain-language category and is never the first thing a stranger must decode.
- SELF-AS-SUBJECT (category: self_as_subject): the SUBJECT of the article must be the thing/field itself
  (what Virtuals ACP is, what the agent economy is, how a protocol works) explained to a reader NEW to the
  field -- NOT the writer's own experience or investigation. Hands-on primary-source work (reading the SDK,
  the contract, hitting the API) is EVIDENCE that backs claims about the subject; it must never become the
  topic. Penalize if a newcomer finishes knowing mainly \"what the author did\" rather than \"what the thing
  IS and why it matters.\" Tell: the piece reads as a personal log/blog of an experience.
  BAD frame: 'バーチャルズの求人市場を覗いてみた話 / 私が確かめたこと' (subject = my visit)
  GOOD frame: 'エージェント同士が仕事を売買する市場はこう動く（実際にSDKとコントラクトを読んで確かめた）'
             (subject = how the market works; the reading is evidence)
- CHRONOLOGICAL-DIARY STRUCTURE: does the piece follow the order the writer investigated things (\"first I
  checked X, then I found Y\") rather than the order the READER cares about? Quote the tell if present.
- INTERNAL-CONTEXT LEAK: any internal person's name (e.g. \"Dais\"), internal spec/document filename, or
  internal-only path/tool name that only makes sense to the writing team, not an external reader
- MEANDERING: sections/paragraphs that do not advance a single spine, detours, restating the same point

Then output the FINAL LINE as pure JSON exactly (no other keys, no trailing commentary after it).
For each TITLE JARGON hit, output a deduction entry with category \"title_jargon\":
{\"scores\":{\"lead\":N,\"one_reader\":N,\"promise\":N,\"why_pay\":N,\"jargon_defined\":N},
\"positive_total\":N,\"deductions\":[{\"category\":\"jargon_density\"|\"title_jargon\"|
\"self_as_subject\"|\"chronological_diary\"|\"internal_context_leak\"|\"meandering\",\"detail\":\"<quote + why>\"}],
\"final_score\":N,\"improvements\":[\"<concrete, actionable instruction, one per real problem found above>\"]}
Where positive_total = sum of the 5 scores (max 100), final_score = positive_total minus 5 points per
deduction entry (floor 0), and improvements lists ONE line per distinct problem found in either the
positive-axis analysis or the negative criteria (empty array only if genuinely nothing to fix).

=== ARTICLE (lang=$LANG_A) ===
$(cat "$MD")"

# Judge broker routing must survive agent subshells that drop env vars
# (observed 2026-07-25): the markdown lives in the run dir, so derive
# ARTICLE_RUN_DIR from it whenever the caller failed to pass one.
if [ -z "${ARTICLE_RUN_DIR:-}" ] && [ -f "$MD" ]; then
  export ARTICLE_RUN_DIR="$(cd "$(dirname "$MD")" && pwd)"
fi
OUT=$(printf '%s' "$PROMPT" | "$MODEL_RUNNER" judge --prompt-file - 2>/dev/null)
JSON=$(printf '%s\n' "$OUT" | grep -o '{"scores".*}' | tail -1)
if [ -z "$JSON" ]; then
  log_gate_verdict "FATAL:no-json-from-judge"
  echo "FATAL: judge returned no JSON verdict" >&2
  printf '%s\n' "$OUT" | tail -5 >&2
  exit 3
fi

# Lane A: drop the two lane-B-only axes from deductions (and their matching improvement lines)
# before scoring -- SKILL.md rule 7. positive_total is untouched (those axes aren't part of it);
# final_score is recomputed as positive_total minus 5 per REMAINING deduction.
JSON=$(printf '%s' "$JSON" | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
lane = sys.argv[1]
if lane == 'a':
    lane_b_only = {'self_as_subject', 'chronological_diary'}
    dropped = [x for x in d.get('deductions', []) if x.get('category') in lane_b_only]
    d['deductions'] = [x for x in d.get('deductions', []) if x.get('category') not in lane_b_only]
    if dropped:
        dropped_quotes = [x.get('detail', '') for x in dropped]
        d['improvements'] = [imp for imp in d.get('improvements', [])
                              if not any(q[:20] and q[:20] in imp for q in dropped_quotes)]
    d['positive_total'] = sum(d.get('scores', {}).values())
    d['final_score'] = max(0, d['positive_total'] - 5 * len(d['deductions']))
    d['lane_a_axes_skipped'] = sorted(lane_b_only) if dropped else []
print(json.dumps(d, separators=(',', ':'), ensure_ascii=False))
" "$LANE" 2>/dev/null || printf '%s' "$JSON")

FINAL_SCORE=$(printf '%s' "$JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('final_score', -1))" 2>/dev/null <<< "$JSON")
if [ -z "$FINAL_SCORE" ] || [ "$FINAL_SCORE" = "-1" ]; then
  log_gate_verdict "FATAL:no-final-score"
  echo "FATAL: judge JSON missing final_score" >&2
  exit 3
fi

VERDICT="FAIL"
python3 -c "import sys; sys.exit(0 if float('$FINAL_SCORE') >= $TH else 1)" && VERDICT="PASS"

MERGED_JSON=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
d['verdict'] = sys.argv[2]
print(json.dumps(d, separators=(',', ':'), ensure_ascii=False))
" "$JSON" "$VERDICT" 2>/dev/null || printf '%s' "$JSON")
[ "$GATE_CONTROL_ACTIVE" -eq 0 ] || printf '%s\n' "$MERGED_JSON" >"$GATE_OUTPUT_FILE"
echo "$MERGED_JSON"
log_gate_verdict "$VERDICT (score=$FINAL_SCORE/$TH lane=$LANE)"
[ "$VERDICT" = "PASS" ]
