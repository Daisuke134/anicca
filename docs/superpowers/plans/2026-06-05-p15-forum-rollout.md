# P15 forum-rollout (#338) — IMPLEMENTATION PLAN

Spec: `docs/superpowers/specs/2026-06-05-p15-forum-rollout-design.md`
Branch: `feat/p15-forum-rollout` · Worktree: `.worktrees/p15-forum-rollout/`
All paths relative to the worktree root unless absolute. `JQ=/usr/bin/jq`.

TDD per task: write/extend test → run RED → implement → run GREEN.

---

## Task 0 — worktree + skeleton (setup)

```bash
cd /Users/anicca/anicca-oss
git worktree add .worktrees/p15-forum-rollout -b feat/p15-forum-rollout
mkdir -p .worktrees/p15-forum-rollout/skills/forum-rollout/scripts
mkdir -p .worktrees/p15-forum-rollout/skills/forum-rollout/tests
```
Verify: `git -C .worktrees/p15-forum-rollout branch --show-current` → `feat/p15-forum-rollout`.

---

## Task 1 — `_lib.sh` (RED via test_lib.sh first)

Write `skills/forum-rollout/tests/test_lib.sh` asserting the helpers below, then implement
`skills/forum-rollout/scripts/_lib.sh`.

`_lib.sh` contents (complete):

```bash
#!/usr/bin/env bash
# Shared helpers for forum-rollout (#338 P15). Sourced by rollout.sh / run.sh.
# No top-level side effects beyond mkdir of the state dir.
# shellcheck shell=bash
JQ="${JQ:-/usr/bin/jq}"
REPO="${FORUM_REPO:-Daisuke134/anicca-oss}"
STATE_DIR="${STATE_DIR:-$HOME/.hermes/state}"
ROLLOUT_LOG="$STATE_DIR/forum-rollout.jsonl"

# Skills/targets Anicca may NEVER roll out against (canonical chokepoints; only Dais edits).
HARD_NO_LIST="anicca-constitution-guard eval-loop anicca-payout-ubi anicca-wallet forum-rollout"

# Resolve self-manage handler dir + guard (overridable for tests).
FR_SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FR_SKILLS_ROOT="$(cd "$FR_SKILL_DIR/.." && pwd)"
SELF_MANAGE_DIR="${FR_SELF_MANAGE_DIR:-$FR_SKILLS_ROOT/self-manage/scripts}"
GUARD_CHECK="${FR_GUARD_CHECK:-$FR_SKILLS_ROOT/anicca-constitution-guard/scripts/check.sh}"

mkdir -p "$STATE_DIR"
touch "$ROLLOUT_LOG"

fr_mktemp() { mktemp "$STATE_DIR/.tmp-fr-${1:-x}-XXXX.$$"; }

# fr_extract_block <comment-body> → if it has a CONSENSUS: marker AND a ```rollout fence,
# echo the fence body (between ```rollout and the next ```). Else echo nothing, return 1.
fr_extract_block() {
  local body="$1"
  printf '%s\n' "$body" | grep -Eq '^[[:space:]]*CONSENSUS:' || return 1
  printf '%s\n' "$body" | awk '
    /^[[:space:]]*```rollout[[:space:]]*$/ {inb=1; next}
    inb && /^[[:space:]]*```[[:space:]]*$/ {inb=0; exit}
    inb {print}
  ' | grep -q . || return 1
  printf '%s\n' "$body" | awk '
    /^[[:space:]]*```rollout[[:space:]]*$/ {inb=1; next}
    inb && /^[[:space:]]*```[[:space:]]*$/ {inb=0; exit}
    inb {print}
  '
}

# fr_field <block> <KEY> → value of "KEY: ..." (case-insensitive key), trimmed.
fr_field() {
  printf '%s\n' "$1" | grep -iE "^[[:space:]]*$2:" | head -1 \
    | sed -E "s/^[[:space:]]*[A-Za-z-]+:[[:space:]]*//" | sed -E 's/[[:space:]]+$//'
}

# fr_payload <block> → the PAYLOAD JSON (everything after PAYLOAD:), or {} if absent/invalid.
fr_payload() {
  local raw
  raw="$(printf '%s\n' "$1" | grep -iE '^[[:space:]]*PAYLOAD:' | head -1 \
    | sed -E 's/^[[:space:]]*[Pp][Aa][Yy][Ll][Oo][Aa][Dd]:[[:space:]]*//')"
  [ -n "$raw" ] || { echo '{}'; return 0; }
  printf '%s' "$raw" | "$JQ" -ce . >/dev/null 2>&1 && printf '%s' "$raw" || echo '{}'
}

# fr_consensus_sha <consensus-marker-line> <block> → 64-hex sha256 (idempotency key).
fr_consensus_sha() {
  printf '%s\n%s' "$1" "$2" | /usr/bin/shasum -a 256 | cut -c1-64
}

# fr_hard_no <target> → exit 0 (BLOCK) if target matches any HARD-NO token as a whole
# word or path segment. exit 1 = allowed.
fr_hard_no() {
  local t="$1" tok
  for tok in $HARD_NO_LIST; do
    [ "$t" = "$tok" ] && return 0
    case "$t" in
      *"/$tok/"*|*"/$tok"|"$tok/"*) return 0 ;;
      *" $tok "*|"$tok "*|*" $tok") return 0 ;;
    esac
  done
  return 1
}

# fr_applied <issue_n> <sha> → exit 0 if (issue_n, sha) already in the log (idempotency).
fr_applied() {
  [ -s "$ROLLOUT_LOG" ] || return 1
  "$JQ" -e --argjson n "$1" --arg s "$2" \
    'select(.issue_n==$n and .consensus_sha==$s)' "$ROLLOUT_LOG" >/dev/null 2>&1
}

# fr_log <issue_n> <sha> <action_type> <target> <applied bool> <exit_code> <evidence>
fr_log() {
  "$JQ" -nc --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --argjson issue_n "$1" --arg consensus_sha "$2" --arg action_type "$3" \
    --arg target "$4" --argjson applied "$5" --argjson exit_code "$6" --arg evidence_url "$7" \
    '{ts:$ts, issue_n:$issue_n, consensus_sha:$consensus_sha, action_type:$action_type,
      target:$target, applied:$applied, exit_code:$exit_code, evidence_url:$evidence_url}' \
    >> "$ROLLOUT_LOG"
}

# fr_guard <summary> → guard exit code. Fail-closed if guard missing.
fr_guard() {
  [ -x "$GUARD_CHECK" ] || { echo "forum-rollout: guard not executable: $GUARD_CHECK" >&2; return 99; }
  "$GUARD_CHECK" --action "$1" >/dev/null 2>&1
}

# fr_build_argv <action_type> <target> <payload-json> → merged JSON for self-manage handlers.
fr_build_argv() {
  local at="$1" target="$2" pj="$3"
  case "$at" in
    edit-skill)        printf '%s' "$pj" | "$JQ" -c --arg t "$target" '. * {type:"skill-edit", skill:($t), reason:(.reason // "forum consensus")}' ;;
    edit-heartbeat)    printf '%s' "$pj" | "$JQ" -c --arg t "$target" '. * {type:"heartbeat", schedule:(.schedule // $t), reason:(.reason // "forum consensus")}' ;;
    spawn-clone)       printf '%s' "$pj" | "$JQ" -c --arg t "$target" '. * {type:"spawn", name:(.name // $t), reason:(.reason // "forum consensus")}' ;;
    architecture-shift) printf '%s' "$pj" | "$JQ" -c --arg t "$target" '. * {type:"arch-shift", title:(.title // $t), body:(.body // ""), reason:(.reason // "forum consensus")}' ;;
    *) return 1 ;;
  esac
}
```

`test_lib.sh` (complete) — mirrors forum-issues test style:

```bash
#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")/../scripts" && pwd)"
export STATE_DIR="$HOME/.hermes/state/.fr-test-lib.$$"
mkdir -p "$STATE_DIR"; trap 'rm -rf "$STATE_DIR"' EXIT
# shellcheck disable=SC1091
source "$DIR/_lib.sh"
pass=0; fail=0
ok(){ pass=$((pass+1)); echo "  ok: $1"; }
bad(){ fail=$((fail+1)); echo "  FAIL: $1"; }

BLOCK_BODY=$'CONSENSUS: ship it\n\n```rollout\nACTION: architecture-shift\nTARGET: merge-foo-bar\nPAYLOAD: {"reason":"agreed","title":"merge foo+bar"}\n```'
NO_FENCE=$'CONSENSUS: ship it but no block here'
NO_MARKER=$'```rollout\nACTION: edit-skill\nTARGET: daily-report\n```'

blk="$(fr_extract_block "$BLOCK_BODY")" && ok "extract: happy path" || bad "extract: happy path"
fr_extract_block "$NO_FENCE" >/dev/null && bad "extract: no-fence must fail" || ok "extract: no-fence fails"
fr_extract_block "$NO_MARKER" >/dev/null && bad "extract: no-marker must fail" || ok "extract: no-marker fails"

[ "$(fr_field "$blk" ACTION)" = "architecture-shift" ] && ok "field ACTION" || bad "field ACTION ($(fr_field "$blk" ACTION))"
[ "$(fr_field "$blk" TARGET)" = "merge-foo-bar" ] && ok "field TARGET" || bad "field TARGET"
[ "$(fr_payload "$blk" | "$JQ" -r .title)" = "merge foo+bar" ] && ok "payload parse" || bad "payload parse"

s1="$(fr_consensus_sha "CONSENSUS: ship it" "$blk")"
s2="$(fr_consensus_sha "CONSENSUS: ship it" "$blk")"
s3="$(fr_consensus_sha "CONSENSUS: ship it" "different")"
[ "$s1" = "$s2" ] && ok "sha stable" || bad "sha stable"
[ "$s1" != "$s3" ] && ok "sha differs on content" || bad "sha differs"
[ "${#s1}" = "64" ] && ok "sha is 64 hex" || bad "sha len ${#s1}"

fr_hard_no "anicca-wallet" && ok "hard-no: wallet blocked" || bad "hard-no: wallet"
fr_hard_no "eval-loop" && ok "hard-no: eval-loop blocked" || bad "hard-no: eval-loop"
fr_hard_no "forum-rollout" && ok "hard-no: self blocked" || bad "hard-no: self"
fr_hard_no "daily-report" && bad "hard-no: normal skill must pass" || ok "hard-no: normal skill allowed"

av="$(fr_build_argv architecture-shift merge-foo-bar "$(fr_payload "$blk")")"
[ "$(printf '%s' "$av" | "$JQ" -r .type)" = "arch-shift" ] && ok "argv type" || bad "argv type"
[ "$(printf '%s' "$av" | "$JQ" -r .title)" = "merge foo+bar" ] && ok "argv title from payload" || bad "argv title"
av2="$(fr_build_argv edit-skill daily-report '{}')"
[ "$(printf '%s' "$av2" | "$JQ" -r .skill)" = "daily-report" ] && ok "argv edit-skill skill=target" || bad "argv edit-skill"
fr_build_argv bogus x '{}' >/dev/null 2>&1 && bad "argv: unknown action must fail" || ok "argv: unknown action fails"

fr_applied 11 "$s1" && bad "applied: empty=false" || ok "applied: empty false"
fr_log 11 "$s1" architecture-shift merge-foo-bar false 0 dry-run
fr_applied 11 "$s1" && ok "applied: after log=true" || bad "applied: after log"
fr_applied 11 "$s3" && bad "applied: other sha=false" || ok "applied: other sha false"

echo "---"; echo "PASS=$pass FAIL=$fail"; [ "$fail" -eq 0 ]
```

Run: `bash skills/forum-rollout/tests/test_lib.sh` → expect `FAIL=0`.

---

## Task 2 — `rollout.sh` (main) + E2E test

Write `tests/test_rollout_e2e.sh` (offline) first (RED), then implement `rollout.sh`.

`rollout.sh` (complete):

```bash
#!/usr/bin/env bash
# rollout.sh — #338 P15: CONSENSUS → action. Scans issues' threads for a
# `CONSENSUS:` marker + ```rollout fence, guards + denylists, dispatches to
# self-manage handlers (or gh), logs the decision, comments + closes on success.
# Dry-run by default; --confirm executes. Idempotent on (issue_n, consensus_sha).
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/_lib.sh"

MODE="dry-run"
[ "${1:-}" = "--confirm" ] && MODE="confirm"
[ "${1:-}" = "--dry-run" ] && MODE="dry-run"

# Data seam: real gh, or fixtures when FR_FIXTURE_DIR is set (offline tests).
fr_list_issues() {
  if [ -n "${FR_FIXTURE_DIR:-}" ]; then "$JQ" -c '.[]' "$FR_FIXTURE_DIR/issues.json"; else
    gh api "repos/$REPO/issues?state=open&per_page=100" --paginate \
      | "$JQ" -c '.[] | select(.pull_request|not) | {number:.number, body:(.body // "")}'
  fi
}
fr_thread() {
  local n="$1"
  if [ -n "${FR_FIXTURE_DIR:-}" ]; then "$JQ" -c '.[]' "$FR_FIXTURE_DIR/thread-$n.json"; else
    gh api "repos/$REPO/issues/$n/comments" --paginate \
      | "$JQ" -c '.[] | {id:.id, body:(.body // "")}'
  fi
}

dispatch() {
  local at="$1" target="$2" pj="$3" out="" rc=0
  case "$at" in
    edit-skill|edit-heartbeat|spawn-clone|architecture-shift)
      local argv handler; handler="$SELF_MANAGE_DIR/$at.sh"
      argv="$(fr_build_argv "$at" "$target" "$pj")" || { echo "BLOCKED:bad-argv"; return 90; }
      [ -x "$handler" ] || { echo "ERROR:handler-missing:$handler"; return 91; }
      if [ "$MODE" = "confirm" ]; then out="$("$handler" "$argv" 2>&1)"; rc=$?
      else out="$(DRY_RUN=1 "$handler" "$argv" 2>&1)"; rc=$?; fi
      printf '%s' "$out" | grep -oE 'https?://[^ ]+' | head -1 || printf 'exit-%d' "$rc"
      return "$rc" ;;
    merge-pr)
      if [ "$MODE" = "confirm" ]; then gh pr merge "$target" --squash --delete-branch --repo "$REPO" >/dev/null 2>&1; rc=$?
      else echo "DRYRUN gh pr merge $target --squash"; rc=0; fi
      echo "pr#$target"; return "$rc" ;;
    close-issue)
      if [ "$MODE" = "confirm" ]; then gh issue close "$target" --repo "$REPO" --comment "rolled out (#338 forum-rollout)" >/dev/null 2>&1; rc=$?
      else echo "DRYRUN gh issue close $target"; rc=0; fi
      echo "issue#$target"; return "$rc" ;;
    open-pr)
      local title head base body
      title="$(printf '%s' "$pj" | "$JQ" -r '.title // "@anicca rollout PR"')"
      head="$(printf '%s' "$pj" | "$JQ" -r '.head // empty')"
      base="$(printf '%s' "$pj" | "$JQ" -r '.base // "main"')"
      body="$(printf '%s' "$pj" | "$JQ" -r '.body // "Filed by forum-rollout (#338)."')"
      if [ "$MODE" = "confirm" ]; then out="$(gh pr create --repo "$REPO" --title "$title" --head "$head" --base "$base" --body "$body" 2>&1)"; rc=$?; printf '%s' "$out" | grep -oE 'https?://[^ ]+' | head -1 || echo "exit-$rc"
      else echo "DRYRUN gh pr create --title '$title' --head '$head'"; rc=0; fi
      return "$rc" ;;
    *) echo "BLOCKED:unknown-action"; return 90 ;;
  esac
}

process_issue() {
  local issue="$1" n body
  n="$(printf '%s' "$issue" | "$JQ" -r '.number')"
  body="$(printf '%s' "$issue" | "$JQ" -r '.body')"

  # Build candidate source list: issue body + each comment body (newest-first preference
  # is irrelevant — we act on the FIRST source that yields a rollout block).
  local srcs=() s
  srcs+=("$body")
  while IFS= read -r c; do
    [ -n "$c" ] || continue
    srcs+=("$(printf '%s' "$c" | "$JQ" -r '.body')")
  done <<< "$(fr_thread "$n")"

  for s in "${srcs[@]}"; do
    local blk; blk="$(fr_extract_block "$s")" || continue
    local marker; marker="$(printf '%s\n' "$s" | grep -iE '^[[:space:]]*CONSENSUS:' | head -1)"
    local sha; sha="$(fr_consensus_sha "$marker" "$blk")"
    if fr_applied "$n" "$sha"; then echo "rollout: issue #$n already-applied (sha ${sha:0:8})"; return 0; fi

    local at target pj
    at="$(fr_field "$blk" ACTION)"; target="$(fr_field "$blk" TARGET)"; pj="$(fr_payload "$blk")"
    [ -n "$at" ] && [ -n "$target" ] || { echo "rollout: issue #$n malformed block — skip"; fr_log "$n" "$sha" "${at:-none}" "${target:-none}" false 90 "BLOCKED:malformed"; return 0; }

    local summary="Roll out forum CONSENSUS on issue #$n: $at on '$target'. Source: anicca-oss collective forum."
    if ! fr_guard "$summary"; then
      local grc=$?; echo "rollout: issue #$n BLOCKED by guard (exit $grc)"; fr_log "$n" "$sha" "$at" "$target" false "$grc" "BLOCKED:guard"; return 0
    fi
    if fr_hard_no "$target"; then
      echo "rollout: issue #$n TARGET '$target' on HARD-NO list — BLOCKED"; fr_log "$n" "$sha" "$at" "$target" false 2 "BLOCKED:hard-no-list"; return 0
    fi

    echo "rollout: issue #$n dispatch $at '$target' (mode=$MODE)"
    local ev rc applied
    ev="$(dispatch "$at" "$target" "$pj")"; rc=$?
    if [ "$MODE" = "confirm" ] && [ "$rc" -eq 0 ]; then applied=true; else applied=false; fi
    fr_log "$n" "$sha" "$at" "$target" "$applied" "$rc" "$ev"

    if [ "$MODE" = "confirm" ] && [ "$rc" -eq 0 ]; then
      gh api --method POST "repos/$REPO/issues/$n/comments" -f body="✅ rolled out: $at \`$target\`. Evidence: $ev" >/dev/null 2>&1 || true
      gh issue close "$n" --repo "$REPO" --comment "rolled out (#338 forum-rollout)" >/dev/null 2>&1 || true
    fi
    return 0
  done
  echo "rollout: issue #$n no rollout block — skip"
}

main() {
  local any=0
  while IFS= read -r issue; do
    [ -n "$issue" ] || continue
    any=1; process_issue "$issue"
  done <<< "$(fr_list_issues)"
  [ "$any" = "1" ] || echo "rollout: no open issues"
}
main "$@"
```

`tests/test_rollout_e2e.sh` (complete, offline):

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../scripts" && pwd)"
export STATE_DIR="$HOME/.hermes/state/.fr-test-e2e.$$"
WORK="$STATE_DIR/work"; mkdir -p "$WORK"
trap 'rm -rf "$STATE_DIR"' EXIT
pass=0; fail=0
ok(){ pass=$((pass+1)); echo "  ok: $1"; }
bad(){ fail=$((fail+1)); echo "  FAIL: $1"; }

# fake self-manage handler dir: stub that records its JSON arg + exits 0.
SM="$WORK/sm"; mkdir -p "$SM"
cat > "$SM/architecture-shift.sh" <<'EOF'
#!/usr/bin/env bash
echo "STUB-ARCH-SHIFT arg=$1" >> "$STATE_DIR/stub.log"
echo "architecture-shift: FILED https://github.com/x/y/issues/99"
exit 0
EOF
chmod +x "$SM/architecture-shift.sh"
# fake guard: always allow.
GUARD="$WORK/guard.sh"; printf '#!/usr/bin/env bash\nexit 0\n' > "$GUARD"; chmod +x "$GUARD"

# fixture issue + thread with CONSENSUS: + rollout fence.
FX="$WORK/fx"; mkdir -p "$FX"
cat > "$FX/issues.json" <<'EOF'
[{"number":11,"body":"arch-shift proposal, no block in body"}]
EOF
cat > "$FX/thread-11.json" <<'EOF'
[{"id":1,"body":"discussion ..."},
 {"id":2,"body":"CONSENSUS: merge it\n\n```rollout\nACTION: architecture-shift\nTARGET: merge-foo-bar\nPAYLOAD: {\"reason\":\"agreed\",\"title\":\"merge foo+bar\"}\n```"}]
EOF

export FR_SELF_MANAGE_DIR="$SM" FR_GUARD_CHECK="$GUARD" FR_FIXTURE_DIR="$FX" STATE_DIR
LOG="$STATE_DIR/forum-rollout.jsonl"

bash "$ROOT/rollout.sh" --dry-run >/dev/null 2>&1 || true

grep -q 'STUB-ARCH-SHIFT' "$STATE_DIR/stub.log" 2>/dev/null && ok "handler invoked" || bad "handler invoked"
grep -q 'merge foo+bar' "$STATE_DIR/stub.log" 2>/dev/null && ok "argv carries title" || bad "argv carries title"
n="$(/usr/bin/jq -s 'map(select(.action_type=="architecture-shift" and .applied==false))|length' "$LOG" 2>/dev/null)"
[ "$n" = "1" ] && ok "one jsonl row applied=false" || bad "jsonl row (got $n)"

# idempotency: re-run → no second row.
bash "$ROOT/rollout.sh" --dry-run >/dev/null 2>&1 || true
n2="$(/usr/bin/jq -s 'length' "$LOG" 2>/dev/null)"
[ "$n2" = "1" ] && ok "idempotent: still 1 row" || bad "idempotent (got $n2)"

echo "---"; echo "PASS=$pass FAIL=$fail"; [ "$fail" -eq 0 ]
```

Run RED before rollout.sh exists: `bash tests/test_rollout_e2e.sh` → fails (no script).
After implementing: → `FAIL=0`.

---

## Task 3 — `run.sh` wrapper (cron entry)

```bash
#!/usr/bin/env bash
# run.sh — cron entry for forum-rollout (#338). --confirm IFF the Dais escape-hatch
# flag ~/.hermes/state/rollout-allow.flag exists; else --dry-run (Wave-1 safe default).
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
FLAG="${ROLLOUT_ALLOW_FLAG:-$HOME/.hermes/state/rollout-allow.flag}"
if [ -f "$FLAG" ]; then exec "$DIR/rollout.sh" --confirm; else exec "$DIR/rollout.sh" --dry-run; fi
```
`chmod +x` all three scripts.

---

## Task 4 — SKILL.md + README.md

SKILL.md frontmatter (name, description with triggers: "forum rollout", "consensus action",
"roll out", "#338") + usage table. README.md = one-screen operator doc (modes, flag, log path,
HARD-NO list). Content in spec §8.

---

## Task 5 — run all tests + shellcheck

```bash
bash skills/forum-rollout/tests/test_lib.sh
bash skills/forum-rollout/tests/test_rollout_e2e.sh
command -v shellcheck >/dev/null && shellcheck skills/forum-rollout/scripts/*.sh || echo "shellcheck absent — skip"
```
Both tests `FAIL=0`.

---

## Task 6 — hermes wrapper + cron

```bash
cat > ~/.hermes/scripts/forum-rollout.sh <<'EOF'
#!/usr/bin/env bash
# Wrapper for forum-rollout (#338 P15). Real file (NOT symlink) per hermes traversal-guard.
CANON=/Users/anicca/anicca-oss/skills/forum-rollout/scripts/run.sh
WORKTREE=/Users/anicca/anicca-oss/.worktrees/p15-forum-rollout/skills/forum-rollout/scripts/run.sh
if [ -x "$CANON" ]; then exec "$CANON" "$@"; else exec "$WORKTREE" "$@"; fi
EOF
chmod +x ~/.hermes/scripts/forum-rollout.sh
hermes cron add --script forum-rollout.sh --schedule "every 180m" --no-agent
hermes cron list | grep forum-rollout
```

---

## Task 7 — live dry-run against real repo + commit/push

```bash
# real gh, dry-run, against Daisuke134/anicca-oss (issue #11 has no block yet → skip is correct)
skills/forum-rollout/scripts/rollout.sh --dry-run
git add -A && git commit -m "feat(forum-rollout): #338 consensus → action loop

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
git push -u origin feat/p15-forum-rollout
```

## Task 8 — verification-before-completion 5-step gate + code review + report SHA/cron id.
