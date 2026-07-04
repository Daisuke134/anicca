#!/usr/bin/env bash
# run.sh — profitable-article-writer 1-wake entrypoint (REQ-4, REQ-4b, REQ-6, REQ-7, REQ-9, REQ-12, REQ-14).
#
# INTERFACE, mirroring skills/self/founder-loop's env-injectable test-mode convention so the wake is
# deterministically testable with no real agent judgment or network call:
#   env in:  ARTICLE_DIR               state dir (STATE.md, state/accounts.json, state/failures.jsonl,
#                                       state/PUBLISHED all live here)
#   env in:  AUTONOMY                  "on" = Mode B (autonomous publish, REQ-7); anything else
#                                       (default "off") = Mode A (draft + notify, REQ-6)
#   env in:  ARTICLE_TEST=1            deterministic test mode — no real research/craft/gate calls; the
#                                       values below are injected instead
#   env in:  ARTICLE_TEST_TOPIC        injected topic string; EMPTY => no viable topic (REQ-4b SKIP)
#   env in:  ARTICLE_TEST_RESEARCH     "sufficient" | "insufficient" (REQ-4b SKIP if insufficient)
#   env in:  ARTICLE_TEST_V0_RESULTS   comma list, one PASS|FAIL per fix+re-gate round (REQ-14, max 3)
#   env in:  ARTICLE_TEST_V05_RESULTS  comma list, one PASS|FAIL per fix+re-gate round (REQ-14, max 3)
#   env in:  ARTICLE_TEST_MODE         named deterministic scenario for isolated sub-path checks, e.g.
#                                       "record_earn_only" => exercises ONLY the record-earn call and
#                                       prints "RECORD_EARN_NO_LLM: true" (REQ-12, PROP-9)
#   writes:  $ARTICLE_DIR/STATE.md     last_wake_result: SKIPPED|DRAFT|PUBLISHED|ABORTED, rounds_used,
#                                      draft_path, publish_url (Mode B only), notify_path (Mode A only)
#   exit:    0 for every LEGITIMATE outcome — SKIPPED/DRAFT/PUBLISHED/ABORTED are all valid, non-error
#            wake results (REQ-4b and REQ-14 are expected control flow, not failures); non-zero only on a
#            genuine harness error.
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SKILL_DIR/lib/config.sh"

ARTICLE_DIR="${ARTICLE_DIR:-}"
if [ -z "$ARTICLE_DIR" ]; then
  echo "run.sh: ARTICLE_DIR is required" >&2
  exit 1
fi
mkdir -p "$ARTICLE_DIR/state"

AUTONOMY="${AUTONOMY:-off}"

# ---------------------------------------------------------------------------------------------------------
# atomic STATE.md writer (REQ-4b/6/7/14): always write to a tmpfile then rename, never a partial STATE.md.
# ---------------------------------------------------------------------------------------------------------
write_state() {
  local tmp
  tmp="$(mktemp "$ARTICLE_DIR/.STATE.md.XXXXXX")"
  cat > "$tmp"
  mv "$tmp" "$ARTICLE_DIR/STATE.md"
}

# ---------------------------------------------------------------------------------------------------------
# json_escape (contract-review FIND-003 fix): escape a free-text value (e.g. the agent-picked $topic, which
# is NOT sanitized upstream) for safe embedding inside a hand-built JSON string, so a quote/backslash/
# newline in the value can never corrupt state/failures.jsonl's one-JSON-object-per-line JSONL contract.
# Escapes backslash, double-quote, and newline (the characters this file's callers can realistically emit);
# uses python3's json.dumps when available for a fully-correct escape, else falls back to a sed pipeline
# covering the same three characters.
# ---------------------------------------------------------------------------------------------------------
json_escape() {
  local val="$1"
  if [ -z "${ARTICLE_FORCE_SED_ESCAPE:-}" ] && command -v python3 >/dev/null 2>&1; then
    python3 -c 'import json, sys; s = json.dumps(sys.argv[1]); print(s[1:-1])' "$val"
  else
    printf '%s' "$val" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | sed -e ':a' -e 'N' -e '$!ba' -e 's/\n/\\n/g'
  fi
}

# ---------------------------------------------------------------------------------------------------------
# REQ-12/PROP-9 isolated sub-path: exercise ONLY the record-earn call, tied to lib/config.sh's declarative
# RECORD_EARN_USES_LLM marker (real logic, not a hardcoded string dump — if the config marker ever flips to
# 1 this refuses instead of blindly asserting no-LLM). record-earn itself (REQ-9/16, V4 real-money receipt
# read) is the Sprint 2 live-integration seam (note sales endpoint / Stripe / on-chain, per funding mode);
# this Sprint 1 check proves the WIRING invariant the real call will run inside.
# ---------------------------------------------------------------------------------------------------------
if [ "${ARTICLE_TEST_MODE:-}" = "record_earn_only" ]; then
  if [ "${RECORD_EARN_USES_LLM:-1}" = "0" ]; then
    echo "RECORD_EARN_NO_LLM: true"
    exit 0
  fi
  echo "RECORD_EARN_NO_LLM: false (RECORD_EARN_USES_LLM != 0 — refusing, fail-closed)" >&2
  exit 1
fi

# ---------------------------------------------------------------------------------------------------------
# 1. Pick topic + assess research (REQ-4, REQ-4b).
# ---------------------------------------------------------------------------------------------------------
if [ "${ARTICLE_TEST:-}" = "1" ]; then
  topic="${ARTICLE_TEST_TOPIC:-}"
  research="${ARTICLE_TEST_RESEARCH:-insufficient}"
else
  # Real topic-pick/research-assessment is AGENT JUDGMENT (per the purity-boundary map in
  # verification-architecture.md) performed by the running model BEFORE invoking this deterministic wake
  # script, never a hardcoded classifier inside this shell file (per building-effective-ai-agents.md).
  # REQ-19/Sprint 2: the running agent supplies its own topic + research-sufficiency verdict via
  # ARTICLE_REAL_TOPIC/ARTICLE_REAL_RESEARCH. Absent/insufficient => fail-closed SKIPPED, the unchanged
  # Sprint-1 default (REQ-4b) — this file itself still makes no topic/research judgment call.
  topic="${ARTICLE_REAL_TOPIC:-}"
  research="${ARTICLE_REAL_RESEARCH:-insufficient}"
fi

if [ -z "$topic" ] || [ "$research" != "sufficient" ]; then
  write_state <<EOF
last_wake_result: SKIPPED
rounds_used: 0
EOF
  echo "WAKE_RESULT: SKIPPED (topic='$topic' research='$research')"
  exit 0
fi

# ---------------------------------------------------------------------------------------------------------
# 2. Research -> decide -> write (craft layer) -> de-slop (REQ-4). generate_draft is the content-gen HOOK:
#    in test mode it renders a deterministic template from the injected topic (no LLM/network call — this
#    orchestrator stays model-agnostic per REQ-1); the REAL craft-writing pass (agent judgment: theme,
#    buy-reason-3-lines, free/paid split, prose) is the Sprint 2 seam that fills this same hook.
# ---------------------------------------------------------------------------------------------------------
generate_draft() {
  local topic="$1" out="$2"
  if [ "${ARTICLE_TEST:-}" != "1" ] && [ -n "${ARTICLE_REAL_DRAFT_PATH:-}" ] && [ -f "${ARTICLE_REAL_DRAFT_PATH:-}" ]; then
    # REQ-19/Sprint 2 real content-gen hook: the running agent (never this deterministic shell script) has
    # ALREADY researched and written the real article to ARTICLE_REAL_DRAFT_PATH, per the purity-boundary
    # map (craft writing = agent judgment, verification-architecture.md). Use that real content VERBATIM.
    # PROP-19 note: this is state (a) of generate_draft's 3-state precedence (verification-architecture.md,
    # PROP-19 row) -- the ONLY state where the boilerplate template below is guaranteed never used. States
    # (b) (topic/research declared but ARTICLE_REAL_DRAFT_PATH absent -- falls through to the boilerplate
    # below as a documented wiring safety-net, never reached by the real daily-executor loop which always
    # supplies the draft together with topic/research) and (c) (nothing supplied -- fail-closed SKIPPED,
    # handled earlier in the wake before generate_draft is even called) are NOT gated by this branch.
    cp "$ARTICLE_REAL_DRAFT_PATH" "$out"
    return 0
  fi
  cat > "$out" <<EOF
# ${topic}: the pattern most people miss in the first 10 hours

Most people trying ${topic} burn 10+ hours before they find the one workflow that actually ships. Here is the compressed version.

## What's free

- The core mental model for ${topic}.
- The buy-reason, in three lines: (1) speed — skip the trial-and-error, (2) certainty — a checklist that works today, (3) leverage — reuse it on every future project.
- Why the split exists: the What is free here, the How is paid below.

## How it works (paid)

The full step-by-step, plus the exact configs, live in the paid section.

CTA: Get the full walkthrough → https://note.com/example/n/paid-guide
EOF
}

draft_path="$ARTICLE_DIR/draft.md"
generate_draft "$topic" "$draft_path"

# ---------------------------------------------------------------------------------------------------------
# 3. V0/V0.5 gate loop, <=3 rounds (REQ-5, REQ-14). Each round calls the REAL gate scripts (gates/v0.sh,
#    gates/v05.sh); in test mode the per-round result is FORCED via ARTICLE_TEST_FORCE_V0/V05 so the wiring
#    is exercised end-to-end without needing the mechanical checklist itself to be satisfied.
# ---------------------------------------------------------------------------------------------------------
IFS=',' read -r -a V0_ARR <<< "${ARTICLE_TEST_V0_RESULTS:-FAIL}"
IFS=',' read -r -a V05_ARR <<< "${ARTICLE_TEST_V05_RESULTS:-FAIL}"

round=1
success=0
last_v0="FAIL"
last_v05="FAIL"
while :; do
  idx=$((round - 1))
  v0_len=${#V0_ARR[@]}
  v05_len=${#V05_ARR[@]}
  if [ "$idx" -lt "$v0_len" ]; then v0_val="${V0_ARR[$idx]}"; else v0_val="${V0_ARR[$((v0_len - 1))]}"; fi
  if [ "$idx" -lt "$v05_len" ]; then v05_val="${V05_ARR[$idx]}"; else v05_val="${V05_ARR[$((v05_len - 1))]}"; fi
  last_v0="$v0_val"
  last_v05="$v05_val"

  v0_rc=0; v05_rc=0
  if [ "${ARTICLE_TEST:-}" = "1" ]; then
    ARTICLE_TEST_FORCE_V0="$v0_val" bash "$SKILL_DIR/gates/v0.sh" "$draft_path" >/dev/null 2>&1 || v0_rc=$?
    ARTICLE_TEST_FORCE_V05="$v05_val" bash "$SKILL_DIR/gates/v05.sh" "$draft_path" >/dev/null 2>&1 || v05_rc=$?
  else
    bash "$SKILL_DIR/gates/v0.sh" "$draft_path" >/dev/null 2>&1 || v0_rc=$?
    bash "$SKILL_DIR/gates/v05.sh" "$draft_path" >/dev/null 2>&1 || v05_rc=$?
  fi

  if [ "$v0_rc" -eq 0 ] && [ "$v05_rc" -eq 0 ]; then
    success=1
    break
  fi

  if [ "$round" -ge 3 ]; then
    break
  fi
  round=$((round + 1))
done
rounds_used=$round

# ---------------------------------------------------------------------------------------------------------
# 4a. 3-round ceiling reached with no BOTH-PASS -> ABORT, no publish, ever (REQ-14).
# ---------------------------------------------------------------------------------------------------------
if [ "$success" -ne 1 ]; then
  fail_ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  topic_json="$(json_escape "$topic")"
  fail_line="{\"ts\": \"$fail_ts\", \"topic\": \"$topic_json\", \"rounds_used\": $rounds_used, \"last_v0\": \"$last_v0\", \"last_v05\": \"$last_v05\"}"
  printf '%s\n' "$fail_line" >> "$ARTICLE_DIR/state/failures.jsonl"

  write_state <<EOF
last_wake_result: ABORTED
rounds_used: $rounds_used
draft_path: $draft_path
EOF
  echo "WAKE_RESULT: ABORTED (rounds_used=$rounds_used, last_v0=$last_v0, last_v05=$last_v05)"
  exit 0
fi

# ---------------------------------------------------------------------------------------------------------
# 4b. BOTH-PASS: Mode A (default, AUTONOMY=off) stops at draft + notifies the human; Mode B (AUTONOMY=on)
#     publishes directly then distributes (REQ-6, REQ-7). Mode B's "publish" call goes through the SAME
#     fail-closed gates/publish-gate.sh used by PROP-5, re-run with the already-PASSing forced values so
#     the single wired publish point (the PUBLISHED sentinel) is the one that ever fires.
# ---------------------------------------------------------------------------------------------------------
if [ "$AUTONOMY" = "on" ]; then
  pub_rc=0
  if [ "${ARTICLE_TEST:-}" = "1" ]; then
    ARTICLE_DIR="$ARTICLE_DIR" ARTICLE_TEST_FORCE_V0="$last_v0" ARTICLE_TEST_FORCE_V05="$last_v05" \
      bash "$SKILL_DIR/gates/publish-gate.sh" "$draft_path" >/dev/null 2>&1 || pub_rc=$?
  else
    ARTICLE_DIR="$ARTICLE_DIR" bash "$SKILL_DIR/gates/publish-gate.sh" "$draft_path" >/dev/null 2>&1 || pub_rc=$?
  fi

  if [ "$pub_rc" -ne 0 ]; then
    # Gate re-check disagreed at the publish step (should not happen given a BOTH-PASS round above) —
    # fail-closed: treat as an abort, never a partial publish.
    fail_ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    topic_json="$(json_escape "$topic")"
    printf '%s\n' "{\"ts\": \"$fail_ts\", \"topic\": \"$topic_json\", \"rounds_used\": $rounds_used, \"reason\": \"publish-gate re-check failed\"}" >> "$ARTICLE_DIR/state/failures.jsonl"
    write_state <<EOF
last_wake_result: ABORTED
rounds_used: $rounds_used
draft_path: $draft_path
EOF
    echo "WAKE_RESULT: ABORTED (publish-gate re-check failed)"
    exit 0
  fi

  # Distribution to reach platforms (REQ-7/8/11) is the Sprint 2 live-integration seam — per-rail
  # publishers keyed off identity/accounts.sh's registry. Sprint 1 proves the publish wiring itself.
  write_state <<EOF
last_wake_result: PUBLISHED
rounds_used: $rounds_used
draft_path: $draft_path
publish_url: pending-live-rail-integration
EOF
  echo "WAKE_RESULT: PUBLISHED (rounds_used=$rounds_used)"
  exit 0
fi

# Mode A: stop at draft, notify the human (URL + screenshot) for review — never publish (REQ-6).
#
# REQ-19/Sprint 2, PROP-20: if the caller asked for a real note.com DRAFT (ARTICLE_NOTE_TITLE set), attempt
# it via the REUSED, existing note-publish pipeline (lib/note_publish.sh — never rebuilt here). Any failure
# at any step degrades to the Sprint-1 safe placeholder below; this NEVER crashes the wake and NEVER fakes a
# URL. lib/note_publish.sh's own NOTE_PUBLISH_TEST_FORCE seam keeps this branch hermetically testable
# independent of ARTICLE_TEST (each side-effect area owns its own test-injection seam, same convention as
# ARTICLE_TEST_FORCE_V0/V05 for the gates).
notify_url="pending-human-review"
notify_screenshot="pending-human-review"
if [ -n "${ARTICLE_NOTE_TITLE:-}" ]; then
  # shellcheck disable=SC1091
  source "$SKILL_DIR/lib/note_publish.sh"
  note_out="$(run_note_mode_a_publish "$draft_path" "$ARTICLE_NOTE_TITLE" "${ARTICLE_NOTE_KEY:-new}" "${ARTICLE_NOTE_PRICE:-500}" "${ARTICLE_NOTE_PAYWALL_HEADING:-}" 2>&1)"; note_rc=$?
  if [ $note_rc -eq 0 ]; then
    real_url="$(echo "$note_out" | grep -oE '^NOTE_URL: .*' | sed 's/^NOTE_URL: //')"
    real_shot="$(echo "$note_out" | grep -oE '^NOTE_SCREENSHOT: .*' | sed 's/^NOTE_SCREENSHOT: //')"
    [ -n "$real_url" ] && notify_url="$real_url"
    [ -n "$real_shot" ] && notify_screenshot="$real_shot"
  else
    echo "note-publish wiring did not complete (degrading to the safe placeholder, never faking a URL): $note_out" >&2
  fi
fi

notify_path="$ARTICLE_DIR/notify.json"
notify_tmp="$(mktemp "$ARTICLE_DIR/.notify.json.XXXXXX")"
notify_url_json="$(json_escape "$notify_url")"
notify_shot_json="$(json_escape "$notify_screenshot")"
cat > "$notify_tmp" <<EOF
{"draft_path": "$draft_path", "url": "$notify_url_json", "screenshot": "$notify_shot_json"}
EOF
mv "$notify_tmp" "$notify_path"

write_state <<EOF
last_wake_result: DRAFT
rounds_used: $rounds_used
draft_path: $draft_path
notify_path: $notify_path
EOF
echo "WAKE_RESULT: DRAFT (rounds_used=$rounds_used, notify_path=$notify_path)"
exit 0
