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
#
#   Sprint-2 REAL-MODE env vars (REQ-19; used only when ARTICLE_TEST is NOT "1" — contract-review FIND-007):
#   env in:  ARTICLE_REAL_TOPIC        the running agent's own picked topic (real-mode equivalent of
#                                       ARTICLE_TEST_TOPIC); EMPTY => no viable topic (REQ-4b SKIP)
#   env in:  ARTICLE_REAL_RESEARCH     "sufficient" | "insufficient", the agent's own research-sufficiency
#                                       verdict (real-mode equivalent of ARTICLE_TEST_RESEARCH)
#   env in:  ARTICLE_REAL_DRAFT_PATH   path to the agent's ALREADY-researched-and-written real article;
#                                       used VERBATIM by generate_draft's state (a) (PROP-19). Supplied-but-
#                                       missing is a distinct wiring ERROR, logged to
#                                       $ARTICLE_DIR/state/failures.jsonl (not the same as omitting it)
#   env in:  ARTICLE_NOTE_TITLE        if set, Mode A attempts a REAL note.com DRAFT via lib/note_publish.sh
#                                       (PROP-20); if unset, Mode A keeps the Sprint-1 placeholder
#   env in:  ARTICLE_NOTE_KEY          note.com draft key hint passed to run_note_mode_a_publish (default
#                                       "new" — a genuinely NEW draft, never overwrites an existing article)
#   env in:  ARTICLE_NOTE_PRICE        single one-time ¥ price for the 有料note paid area (default 500)
#   env in:  ARTICLE_NOTE_PAYWALL_HEADING  substring of the heading the paid-area marker is inserted before
#                                       (REQ-5c free/paid split); empty => paid-line insertion is skipped,
#                                       draft stays fully free (lib/note-set-single-price.py)
#
#   Sprint-4 REQ-23/24/25 env vars (real Mode-B in-loop publish, "wire that in"):
#   env in:  ARTICLE_MODEB_RATIO       runtime-mutable "1-in-N" graduation ratio (or bare "N"), consulted
#                                       ONLY when AUTONOMY=on -- REQ-25. Overrides ARTICLE_MODEB_RATIO_FILE
#                                       when both are set. Missing/N=0/negative/non-integer ALL fail closed
#                                       to Mode A for this wake (never Mode B, never a crash).
#   env in:  ARTICLE_MODEB_RATIO_FILE  path to a runtime config/state file holding the SAME ratio value
#                                       (default: $ARTICLE_DIR/state/mode-b-ratio) -- the install-level,
#                                       re-readable-without-redeploy config REQ-25 requires.
#   env in:  ARTICLE_MODEB_NOTE_KEY    an ALREADY-PREPARED (eyecatch+visuals+price confirmed) note.com
#                                       draft key to actually publish for real when this wake resolves to
#                                       Mode B (REQ-23) -- no default/wildcard (same REQ-21 safety
#                                       convention). Absent => degrades to the Sprint-1 safe placeholder,
#                                       never crashes, never fabricates a URL.
#   env in:  ARTICLE_NOTE_BROWSER_COMMON_DIR  TEST-INJECTION ONLY, forwarded to
#                                       lib/note-mode-b-publish.py -- see that file's own docstring.
#   writes:  $ARTICLE_DIR/STATE.md     last_wake_result: SKIPPED|DRAFT|PUBLISHED|ABORTED|UNCONFIRMED,
#                                      rounds_used, draft_path, publish_url (Mode B only),
#                                      publish_verify_result/publish_verified_at (Mode B real-publish only),
#                                      notify_path (Mode A only)
#   exit:    0 for every LEGITIMATE outcome — SKIPPED/DRAFT/PUBLISHED/ABORTED/UNCONFIRMED are all valid,
#            non-error wake results (REQ-4b, REQ-14, and REQ-24's verify-inconclusive path are expected
#            control flow, not failures); non-zero only on a genuine harness error.
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
# REQ-23/REQ-25/PROP-26: the EFFECTIVE per-wake mode, ratio-derived, runtime-mutable, fail-closed to Mode A
# on ANY malformed ratio (missing/uninitialized, N=0, negative, non-integer). AUTONOMY=on is the master
# enable (a safety knob: AUTONOMY=off — the default — is ALWAYS Mode A regardless of ratio); the ratio then
# decides WHICH specific wake, within the graduated 1-in-N cycle, is actually Mode B. REQ-23's Mode-B
# branch-selection below consults ONLY $effective_mode, never a raw AUTONOMY value in isolation.
# ---------------------------------------------------------------------------------------------------------
MODEB_RATIO_FILE="${ARTICLE_MODEB_RATIO_FILE:-$ARTICLE_DIR/state/mode-b-ratio}"
MODEB_COUNTER_FILE="$ARTICLE_DIR/state/mode-b-wake-count"

# stdout: the parsed positive-integer N (accepts a bare "N" or a "1-in-N" string). Prints NOTHING and
# returns 1 on ANY malformed/missing input -- missing/uninitialized (raw empty), N=0, negative (rejected by
# the [0-9]+ shape, never reaches the modulo below), non-integer (same rejection), OR a leading-zero digit
# string (e.g. "08", "09", "1-in-08") -- REQ-25's 4 named cases PLUS the contract-review FIND-001/FIND-002
# leading-zero-octal hazard.
#
# WHY 10#$n, not just a stricter regex: a plain "^[0-9]+$"-validated string like "08" is syntactically
# all-digits, but bash's OWN arithmetic evaluator ($(( )) / numeric "[ -eq ]") parses a leading-zero digit
# string as OCTAL, and "8"/"9" are not valid octal digits -- this raises a runtime "value too great for
# base" error (a crash/stderr leak), not a clean fail-closed. "$((10#$n))" explicitly forces BASE-10
# interpretation of $n, so "08" correctly normalizes to 8 (never misread as octal) regardless of leading
# zeros. This is the single normalization point every caller of $n (both the "-eq 0" check right below and
# the modulo consumer at the AUTONOMY branch) relies on, so the guard is applied ONCE, deliberately, here --
# not incidentally at one call site and absent at another (FIND-002).
_modeb_ratio_n() {
  local raw="${ARTICLE_MODEB_RATIO:-}"
  if [ -z "$raw" ] && [ -f "$MODEB_RATIO_FILE" ]; then
    raw="$(head -n1 "$MODEB_RATIO_FILE" 2>/dev/null | tr -d '[:space:]')"
  fi
  if [ -z "$raw" ]; then
    return 1
  fi
  local digits
  if [[ "$raw" =~ ^1-in-([0-9]+)$ ]]; then
    digits="${BASH_REMATCH[1]}"
  elif [[ "$raw" =~ ^[0-9]+$ ]]; then
    digits="$raw"
  else
    return 1
  fi
  # Explicit base-10 normalization (strips any leading zeros safely) -- if THIS itself somehow fails (e.g.
  # a pathological digit string outside bash's integer range), that is "a parse error" per REQ-25 and MUST
  # fail closed to Mode A exactly like every other malformed case, never crash the wake.
  local n
  if ! n=$((10#$digits)) 2>/dev/null; then
    return 1
  fi
  if [ "$n" -eq 0 ] 2>/dev/null; then
    return 1
  fi
  printf '%s' "$n"
  return 0
}

# Atomically increments and returns the install's own persistent per-wake counter (REQ-25: "1-in-N wakes
# run Mode B" needs a runtime-mutable, cross-invocation counter, not just a stored ratio value). A corrupted
# (non-numeric, OR a leading-zero digit string like "08" -- FIND-001) counter file resets to 0 rather than
# crashing or misresolving. Same "$((10#..))" base-10-forcing normalization as _modeb_ratio_n, applied here
# too (FIND-002: the fix must be consistent at every arithmetic site, not just one).
_modeb_next_wake_count() {
  local cur=0
  if [ -f "$MODEB_COUNTER_FILE" ]; then
    cur="$(cat "$MODEB_COUNTER_FILE" 2>/dev/null | tr -d '[:space:]')"
  fi
  case "$cur" in (''|*[!0-9]*) cur=0 ;; esac
  # Base-10-force the sanitized digit string before arithmetic -- a leading-zero survivor of the above
  # digit-only sanitizer (e.g. a file externally corrupted to "08") would otherwise hit the SAME
  # octal-misparse hazard as the ratio value; a normalization failure here is treated as "corrupted", i.e.
  # resets to 0, exactly like the non-digit case above.
  if ! cur=$((10#$cur)) 2>/dev/null; then
    cur=0
  fi
  local nxt=$((cur + 1))
  local tmp
  tmp="$(mktemp "$ARTICLE_DIR/state/.mode-b-wake-count.XXXXXX")"
  printf '%s\n' "$nxt" > "$tmp"
  mv "$tmp" "$MODEB_COUNTER_FILE"
  printf '%s' "$nxt"
}

effective_mode="A"
if [ "$AUTONOMY" = "on" ]; then
  if ratio_n="$(_modeb_ratio_n)"; then
    wake_n="$(_modeb_next_wake_count)"
    # FIND-002: the SAME explicit, deliberate base-10-forcing guard used inside _modeb_ratio_n's "-eq 0"
    # check is applied HERE too, right before the modulo that actually decides effective_mode -- not just at
    # one call site. Both $wake_n and $ratio_n are already base-10-normalized by their producer functions
    # above, so this re-normalization should always succeed; it exists so THIS site's fail-closed behavior
    # is deliberate/tested (identical guard, identical outcome), never incidental on bash's own arithmetic
    # short-circuiting. Any normalization failure here (belt-and-suspenders) fails closed to Mode A, same as
    # every other malformed-ratio case in REQ-25 -- it never crashes the wake.
    if wake_n_safe=$((10#$wake_n)) 2>/dev/null && ratio_n_safe=$((10#$ratio_n)) 2>/dev/null; then
      if [ $((wake_n_safe % ratio_n_safe)) -eq 0 ]; then
        effective_mode="B"
      fi
    fi
  fi
fi

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
  if [ "${ARTICLE_TEST:-}" != "1" ] && [ -n "${ARTICLE_REAL_DRAFT_PATH:-}" ]; then
    if [ -f "${ARTICLE_REAL_DRAFT_PATH:-}" ]; then
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
    # Sprint-2 contract-review FIND-003 fix: ARTICLE_REAL_DRAFT_PATH was SUPPLIED (non-empty) but the file
    # does NOT exist. This is a DISTINCT, genuine wiring ERROR — not the same as state (b)'s documented
    # "no draft path handed off yet" safety-net, which is defined by the caller never supplying a path at
    # all. A caller that supplied a path with a typo, hit a race where the file hasn't been written yet, or
    # has a real bug in the daily-executor's own wiring must be distinguishable from a caller that simply
    # never intended a real draft — silently falling through to the SAME boilerplate branch as state (b)
    # would hide exactly the class of wiring bug PROP-19 exists to catch (REQ-19's real daily-executor
    # would otherwise silently draft/publish boilerplate instead of the agent's real researched article,
    # completely undetected). Log a clearly-labeled, distinct failure line to state/failures.jsonl — this
    # still degrades to the boilerplate safety-net below (never crashes the wake), but the failure trail now
    # shows WHY.
    local err_ts path_json
    err_ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    path_json="$(json_escape "$ARTICLE_REAL_DRAFT_PATH")"
    printf '%s\n' "{\"ts\": \"$err_ts\", \"error\": \"generate_draft_wiring_error\", \"reason\": \"ARTICLE_REAL_DRAFT_PATH was supplied but the file does not exist\", \"path\": \"$path_json\"}" >> "$ARTICLE_DIR/state/failures.jsonl"
    echo "generate_draft: WIRING ERROR -- ARTICLE_REAL_DRAFT_PATH='$ARTICLE_REAL_DRAFT_PATH' was supplied but does not exist on disk (falling back to the boilerplate safety-net; this is a distinct wiring bug, NOT the documented 'no draft path supplied' state (b), and is now recorded to state/failures.jsonl)" >&2
  fi
  cat > "$out" <<EOF
# ${topic}: the pattern most people miss in the first 10 hours

Most people burn 10+ hours on ${topic} before finding the one workflow that ships. Here is the compressed version.

## What's free

- The core mental model for ${topic}.
- Speed. Skip the trial-and-error.
- Certainty. A checklist that works today.
- Leverage. Reuse it on every future project.
- The What is free here. The How is paid below.

## How it works (paid)

The full step-by-step lives in the paid section. Exact configs included.

CTA: Get the full walkthrough at the paid link below.
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
# 4b. BOTH-PASS: Mode A (effective_mode=A, the default) stops at draft + notifies the human; Mode B
#     (effective_mode=B, REQ-25's ratio-derived value) publishes directly then distributes (REQ-6, REQ-7).
#     Mode B's "publish" call goes through the SAME fail-closed gates/publish-gate.sh used by PROP-5,
#     re-run with the already-PASSing forced values so the single wired publish point (the PUBLISHED
#     sentinel) is the one that ever fires, THEN (REQ-23/24, Sprint 4) reaches the SHARED real-publish unit
#     (lib/note_browser_common.confirm_and_publish, via lib/note-mode-b-publish.py) and its independent
#     in-loop verify -- NEVER the standalone REQ-21 one-off tool, which stays a separate, human-invoked path.
# ---------------------------------------------------------------------------------------------------------
if [ "$effective_mode" = "B" ]; then
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

  # REQ-23/24 (Sprint 4): only fires a REAL publish click when the caller has handed off an
  # ALREADY-PREPARED note draft key (ARTICLE_MODEB_NOTE_KEY, mirroring ARTICLE_NOTE_TITLE's role for Mode
  # A) -- this file never creates/eyecatches/prices a draft itself, only clicks publish on one the caller
  # names explicitly (no default/wildcard key, same REQ-21 safety property). Distribution to reach
  # platforms (REQ-7/8/11) remains a later-sprint live-integration seam.
  modeb_note_key="${ARTICLE_MODEB_NOTE_KEY:-}"

  if [ -n "$modeb_note_key" ]; then
    modeb_publish_py="${NOTE_MCP_PY:-$HOME/.openclaw/skills/_shared/venv-cloak/bin/python3}"
    if [ ! -x "$modeb_publish_py" ]; then
      modeb_publish_py="python3"
    fi

    modeb_out="$("$modeb_publish_py" "$SKILL_DIR/lib/note-mode-b-publish.py" --draft-key "$modeb_note_key" \
      --price "${ARTICLE_NOTE_PRICE:-500}" 2>&1)"; modeb_rc=$?
    modeb_url="$(echo "$modeb_out" | grep -oE '^NOTE_LIVE_URL: .*' | sed 's/^NOTE_LIVE_URL: //')"
    modeb_ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    verify_result="UNCONFIRMED"
    if [ $modeb_rc -eq 0 ] && [ -n "$modeb_url" ]; then
      # REQ-24: independent post-publish verify, the SAME logic as REQ-22's standalone
      # lib/note-verify-live.py -- a SEPARATE process/invocation, never the click's own optimistic claim.
      verify_out="$(python3 "$SKILL_DIR/lib/note-verify-live.py" "$modeb_note_key" 2>&1)"; verify_rc=$?
      if [ $verify_rc -eq 0 ]; then
        verify_result="SUCCESS"
      fi
    else
      echo "run.sh: Mode-B in-loop publish click did not confirm success for draft '$modeb_note_key' (recording UNCONFIRMED, never blindly retry-publishing the same draft in this wake): $modeb_out" >&2
    fi

    if [ "$verify_result" = "SUCCESS" ]; then
      write_state <<EOF
last_wake_result: PUBLISHED
rounds_used: $rounds_used
draft_path: $draft_path
publish_url: $modeb_url
publish_verify_result: SUCCESS
publish_verified_at: $modeb_ts
EOF
      echo "WAKE_RESULT: PUBLISHED (rounds_used=$rounds_used, verify=SUCCESS, draft_key=$modeb_note_key)"
    else
      # REQ-24: verification failure/inconclusive (or the click itself never confirmed success) -- NEVER
      # silently assume success. Record UNCONFIRMED for a later wake or self-heal (REQ-17, Sprint 7) to
      # reconcile; this wake does NOT retry-publish the same draft (this is the only publish attempt made
      # in this wake, by construction — no retry loop exists here).
      write_state <<EOF
last_wake_result: UNCONFIRMED
rounds_used: $rounds_used
draft_path: $draft_path
publish_url: ${modeb_url:-unknown}
publish_verify_result: UNCONFIRMED
publish_verified_at: $modeb_ts
EOF
      echo "WAKE_RESULT: UNCONFIRMED (rounds_used=$rounds_used, draft_key=$modeb_note_key)"
    fi
    exit 0
  fi

  # No real note draft key handed off for this wake (ARTICLE_MODEB_NOTE_KEY unset) -- degrade to the
  # Sprint-1 safe placeholder (unchanged), never crash, never fabricate a URL/verify result. Zero calls to
  # the shared publish function in this branch (PROP-24).
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
