#!/usr/bin/env bash
# verify.sh — fable5-config-slimdown VCSDD verification harness (Phase 2a/RED, re-run for Phase 2b/GREEN)
#
# Purity: this script is READ-ONLY. It never edits, deletes, moves, or creates any file under
# ~/.claude, ~/anicca, or the live checkout. It only reads (grep/jq/wc/diff/md5) and prints
# PASS/FAIL/SKIP lines. Re-run it after each implementation step; it is idempotent.
#
# Tier legend (see specs/verification-architecture.md §Tier legend, feature-specific — NOT the
# vcsdd plugin's default formal-proof tiers 0-3):
#   0 = shell assertion (deterministic file-state: exist/absent/grep/wc/diff/md5)
#   1 = JSON validity (`jq .` parses)
#   2 = E2E / fresh-context adversary judgment — NOT executable by this script; printed as SKIP.
#
# Traceability: each PROP-XXX below implements exactly the row of the same ID in
# specs/verification-architecture.md's "Proof obligations" table.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# tests/ -> <feature>/ -> features/ -> .vcsdd/ -> repo root
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
FEATURE_DIR="${SCRIPT_DIR}/.."
EVIDENCE_DIR="${FEATURE_DIR}/evidence"
BACKUP_DIR="${HOME}/.claude/backups/fable5-slimdown-2026-07-07"
LIVE_CHECKOUT="/Users/anicca/anicca-project"

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# report <PROP-ID> <PASS|FAIL|SKIP> <one-line description>
report() {
  local id="$1" status="$2" desc="$3"
  case "$status" in
    PASS) PASS_COUNT=$((PASS_COUNT + 1)) ;;
    FAIL) FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
    SKIP) SKIP_COUNT=$((SKIP_COUNT + 1)) ;;
  esac
  printf '[%s] %s: %s\n' "$status" "$id" "$desc"
}

as_status() {
  # $1 = shell exit code (0 = true) -> echoes PASS or FAIL
  if [ "$1" -eq 0 ]; then echo PASS; else echo FAIL; fi
}

# ---------------------------------------------------------------------------
# PROP-P1 — REQ-P1: git-context-lite.sh heredoc contradiction removed
# ---------------------------------------------------------------------------
p1_check() {
  local F="${HOME}/.claude/plugins/cache/ww-w-ai/claude-code-token-saver/2.1.0/hooks/git-context-lite.sh"
  [ -f "$F" ] || return 1
  ! grep -q "Never without explicit user request" "$F" \
    && ! grep -q 'Avoid .git add -A' "$F" \
    && grep -q 'CLAUDE.md' "$F" \
    && grep -qi 'secret' "$F" \
    && bash -n "$F"
}
p1_check; report PROP-P1 "$(as_status $?)" "git-context-lite.sh: no contradiction blocks, CLAUDE.md ref present, secrets guidance kept, bash -n OK"

# ---------------------------------------------------------------------------
# PROP-P2a — REQ-P2a: loop-engineering.md deleted + backed up
# ---------------------------------------------------------------------------
p2a_check() {
  [ ! -f "${HOME}/.claude/rules/loop-engineering.md" ] \
    && [ -f "${BACKUP_DIR}/loop-engineering.md" ]
}
p2a_check; report PROP-P2a "$(as_status $?)" "loop-engineering.md deleted + backup exists"

# ---------------------------------------------------------------------------
# PROP-P2b-shell — REQ-P2b: session-architecture.md <=20 lines, banned strings absent, backed up
# ---------------------------------------------------------------------------
p2b_shell_check() {
  local SA="${HOME}/.claude/plugins/cache/ww-w-ai/claude-code-token-saver/2.1.0/hooks/session-architecture.md"
  [ -f "$SA" ] || return 1
  [ "$(wc -l < "$SA")" -le 20 ] \
    && ! grep -qE "Thinking Patterns|Dialectic|runAgent|opus-4-6|Hard bans" "$SA" \
    && [ -f "${BACKUP_DIR}/session-architecture.md" ]
}
p2b_shell_check; report PROP-P2b-shell "$(as_status $?)" "session-architecture.md <=20 lines, banned strings absent, backup exists"

# ---------------------------------------------------------------------------
# PROP-P2b-judgment — REQ-P2b: 4-point semantic content — Tier 2, adversary-only
# ---------------------------------------------------------------------------
report PROP-P2b-judgment SKIP "tier-2: manual — fresh-context adversary confirms 4-point substance in session-architecture.md"

# ---------------------------------------------------------------------------
# PROP-P3a / PROP-SAFE-4 — REQ-P3a: MOVE REF-CHECK evidence log exists with >=27 lines
# ---------------------------------------------------------------------------
MOVE_REF_LOG="${EVIDENCE_DIR}/move-ref-check.log"
p3a_check() {
  [ -f "$MOVE_REF_LOG" ] && [ "$(wc -l < "$MOVE_REF_LOG")" -ge 27 ]
}
p3a_check
P3A_STATUS="$(as_status $?)"
report PROP-P3a "$P3A_STATUS" "move-ref-check.log exists with >=27 recorded grep runs (27 = 3 files x 3 dirs x 3 path forms)"
report PROP-SAFE-4 "$P3A_STATUS" "alias of PROP-P3a (MOVE REF-CHECK gate), same evidence, not re-implemented"

# ---------------------------------------------------------------------------
# PROP-P3b — REQ-P3b: rule files that PASSED the MOVE REF-CHECK gate (PROP-P3a, zero hits
#   outside CLAUDE.md) moved rules/->references/; any file the gate found a real reference for
#   correctly stays in rules/ (this is REQ-P3a's own documented conditional branch: "参照が1件
#   でも見つかった場合...その特定ファイルの移動を中止し...REQ-P3b の当該ファイル分の目標状態は
#   適用されない" — a hardcoded "all 3 must move" assertion would be WRONG per that same spec
#   text, so this check reads move-ref-check.log to determine, per file, whether the gate passed).
# ---------------------------------------------------------------------------
p3b_check() {
  local name gate_passed
  for name in building-voice-agents building-effective-ai-agents loop-command; do
    if [ -f "$MOVE_REF_LOG" ] && grep -q "^file=${name}\.md .*hits=[1-9]" "$MOVE_REF_LOG"; then
      gate_passed=0
    else
      gate_passed=1
    fi
    if [ "$gate_passed" -eq 1 ]; then
      # gate passed (zero hits) -> must have moved
      [ -f "${HOME}/.claude/references/${name}.md" ] || return 1
      [ -f "${HOME}/.claude/rules/${name}.md" ] && return 1
    else
      # gate found a real reference -> must NOT have moved
      [ -f "${HOME}/.claude/rules/${name}.md" ] || return 1
      [ -f "${HOME}/.claude/references/${name}.md" ] && return 1
    fi
  done
  grep -q "references/loop-command.md" "${HOME}/.claude/CLAUDE.md" \
    && ! grep -q "rules/loop-command.md" "${HOME}/.claude/CLAUDE.md" \
    && [ -f "${HOME}/.claude/rules/context7.md" ]
}
p3b_check; report PROP-P3b "$(as_status $?)" "rule files that passed MOVE REF-CHECK moved rules/->references/; files with a real reference correctly left in place; CLAUDE.md references updated; context7.md untouched"

# ---------------------------------------------------------------------------
# PROP-P4 — REQ-P4: SSOT guard snapshot-diff (iteration-2 FIND-005 / iteration-3 FIND-008)
# ---------------------------------------------------------------------------
p4_check() {
  local PRE="${EVIDENCE_DIR}/p4-pre-hooks.json"
  local POST="${EVIDENCE_DIR}/p4-post-hooks.json"
  local LIVE="${HOME}/.claude/settings.json"
  [ -f "$PRE" ] && [ -f "$POST" ] || return 1

  # (a) post's UserPromptSubmit has zero ssot-guard entries
  jq -e '[(.UserPromptSubmit // []) | .[].hooks[]?.command | select(test("ssot-guard"))] | length == 0' "$POST" >/dev/null 2>&1 || return 1

  # (b) structural equivalence: pre with ssot-guard mechanically stripped == post
  #     (// [] on both sides per FIND-008; empty-hooks matcher-groups normalized out on both sides)
  local EXPECTED ACTUAL
  EXPECTED=$(jq -c '(.UserPromptSubmit // []) | map(.hooks |= map(select(.command | test("ssot-guard") | not))) | map(select((.hooks // []) | length > 0)) | sort' "$PRE" 2>/dev/null)
  ACTUAL=$(jq -c '(.UserPromptSubmit // []) | map(select((.hooks // []) | length > 0)) | sort' "$POST" 2>/dev/null)
  [ -n "$EXPECTED" ] && [ "$EXPECTED" = "$ACTUAL" ] || return 1

  # (c) SessionStart byte-identical pre vs post (canonical JSON)
  diff <(jq -S '.SessionStart' "$PRE" 2>/dev/null) <(jq -S '.SessionStart' "$POST" 2>/dev/null) >/dev/null 2>&1 || return 1

  # (d) live file still valid JSON
  jq . "$LIVE" >/dev/null 2>&1
}
p4_check; report PROP-P4 "$(as_status $?)" "settings.json UserPromptSubmit ssot-guard removed via pre/post snapshot-diff, SessionStart unchanged, valid JSON"

# ---------------------------------------------------------------------------
# PROP-P5a — REQ-P5a: adversary-daily.sh --model opus
# ---------------------------------------------------------------------------
p5a_check() {
  grep -q -- '--model opus' "${HOME}/anicca/skills/_shared/adversary-daily.sh"
}
p5a_check; report PROP-P5a "$(as_status $?)" "adversary-daily.sh invokes claude with --model opus"

# ---------------------------------------------------------------------------
# PROP-P5b — REQ-P5b: refusal fallback row in global CLAUDE.md (shell half; judgment half = Tier 2)
# ---------------------------------------------------------------------------
p5b_shell_check() {
  grep -q 'refusal' "${HOME}/.claude/CLAUDE.md"
}
p5b_shell_check
report PROP-P5b "$(as_status $?)" "CLAUDE.md model-division table contains 'refusal' fallback wording (tier-0 half only; tier-2 semantic-correctness half is adversary-only, not scored here)"

# ---------------------------------------------------------------------------
# PROP-P6a — REQ-P6a: worktree .claude/settings.json effortLevel=high
# ---------------------------------------------------------------------------
p6a_check() {
  local F="${ROOT_DIR}/.claude/settings.json"
  [ -f "$F" ] || return 1
  jq -e '.effortLevel == "high"' "$F" >/dev/null 2>&1 && jq . "$F" >/dev/null 2>&1
}
p6a_check; report PROP-P6a "$(as_status $?)" "worktree .claude/settings.json effortLevel == high, valid JSON"

# ---------------------------------------------------------------------------
# PROP-P6b — REQ-P6b: live checkout .claude/settings.json effortLevel=high + pushed
# ---------------------------------------------------------------------------
p6b_check() {
  local F="${LIVE_CHECKOUT}/.claude/settings.json"
  [ -f "$F" ] || return 1
  jq -e '.effortLevel == "high"' "$F" >/dev/null 2>&1 || return 1
  jq . "$F" >/dev/null 2>&1 || return 1
  [ -z "$(git -C "$LIVE_CHECKOUT" status --porcelain .claude/settings.json 2>/dev/null)" ] || return 1
  [ -z "$(git -C "$LIVE_CHECKOUT" log origin/feature/clip-rewards..HEAD --oneline -- .claude/settings.json 2>/dev/null)" ]
}
p6b_check; report PROP-P6b "$(as_status $?)" "live checkout .claude/settings.json effortLevel == high, committed and pushed to origin/feature/clip-rewards"

# ---------------------------------------------------------------------------
# PROP-P6c — REQ-P6c: model-division main row updated
# ---------------------------------------------------------------------------
p6c_check() {
  grep -q 'high。設計・監査・難デバッグ' "${HOME}/.claude/CLAUDE.md"
}
p6c_check; report PROP-P6c "$(as_status $?)" "CLAUDE.md model-division main row states high (xhigh temporary-only)"

# ---------------------------------------------------------------------------
# PROP-P7a — REQ-P7a: 8-file PushNotification wiring, structurally inside the runtime prompt value
#   (iteration-1 FIND-001 / iteration-2 FIND-006 / iteration-3 FIND-007)
# For each file: (a) assign-span byte-identical to git HEAD (per-operation backup convention,
# these 8 files live in the git-tracked ~/anicca repo, so HEAD is the "before this op" reference —
# see REQ-SAFE-1's edge case + iteration-3 FIND-007's per-operation clarification), (b) the window
# between assign-span end and the CURRENT (post-insertion) launch line contains a self-referencing
# concatenation line (VAR="${VAR} ...PushNotification...") for that file's actual variable, (c) the
# CURRENT launch line's exact content still matches the known-good pre-P7a text (captured by hand
# at implementation time, since inserting the append line shifts the launch line to a NEW line
# number that no longer aligns with git HEAD's line numbering — a plain by-line-number diff against
# HEAD would silently miscompare once a line has been inserted before it; for `adversary-daily.sh`
# the expected text intentionally already includes P5a's `--model opus`, per FIND-007's
# per-operation convention: P5a lands before P7a on that file).
# ---------------------------------------------------------------------------
ANICCA_REPO="${HOME}/anicca"

p7a_one() {
  # args: relpath varname start end curr_launch expected_launch_text
  local relpath="$1" varname="$2" start="$3" end="$4" curr_launch="$5" expected_launch="$6"
  local abs="${ANICCA_REPO}/skills/${relpath}"
  [ -f "$abs" ] || return 1

  # (a) assign-span byte-identical to HEAD (unaffected by an insertion strictly after ${end})
  diff <(git -C "$ANICCA_REPO" show "HEAD:skills/${relpath}" 2>/dev/null | sed -n "${start},${end}p") \
       <(sed -n "${start},${end}p" "$abs") >/dev/null 2>&1 || return 1

  # (c) current launch line's content matches the known-good pre-P7a text exactly
  local actual_launch
  actual_launch=$(sed -n "${curr_launch}p" "$abs")
  [ "$actual_launch" = "$expected_launch" ] || return 1

  # (b) window between assign-span end and the current launch line has the self-referencing append line
  local window_start=$((end + 1))
  local window_end=$((curr_launch - 1))
  [ "$window_start" -le "$window_end" ] || return 1
  sed -n "${window_start},${window_end}p" "$abs" \
    | grep -E "^${varname}=.*\\\$\\{?${varname}\\}?.*PushNotification" -q
}

P7A_ALL=0
p7a_one "self/self-fix.sh" "TASK" 67 74 76 \
  'tmux -S "$SOCK" new-session -d -s "$SESSION" "$CLAUDE" --name "$SESSION" --model opus --dangerously-skip-permissions --add-dir "$HOME" -- "$TASK"' || P7A_ALL=1
p7a_one "self/capafy-loop/capafy-loop-cli.sh" "STARTUP" 8 8 13 \
  'tmux -S "$SOCK" new-session -d -s "$SESSION" "$CLAUDE" --name "$SESSION" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -- "$STARTUP"' || P7A_ALL=1
p7a_one "self/reddit-loop/reddit-loop-cli.sh" "STARTUP" 9 9 14 \
  'tmux -S "$SOCK" new-session -d -s "$SESSION" "$CLAUDE" --name "$SESSION" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -- "$STARTUP"' || P7A_ALL=1
p7a_one "self/life-manager-loop/life-manager-loop-cli.sh" "STARTUP" 8 8 13 \
  'tmux -S "$SOCK" new-session -d -s "$SESSION" "$CLAUDE" --name "$SESSION" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -- "$STARTUP"' || P7A_ALL=1
p7a_one "earn/clip-promote/clip-promote-cli.sh" "STARTUP" 24 24 41 \
  '  "$CLAUDE" --name "$SESSION" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -- "$STARTUP"' || P7A_ALL=1
p7a_one "earn/video/video-cli.sh" "STARTUP" 17 17 34 \
  '  "$CLAUDE" --name "$SESSION" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -- "$STARTUP"' || P7A_ALL=1
p7a_one "earn/clip/clip-cli.sh" "STARTUP" 18 18 35 \
  '  "$CLAUDE" --name "$SESSION" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -- "$STARTUP"' || P7A_ALL=1
p7a_one "_shared/adversary-daily.sh" "PROMPT" 20 21 24 \
  'claude -p "$PROMPT" --model opus --output-format text 2>&1 | tee -a "$LOG"' || P7A_ALL=1
report PROP-P7a "$(as_status $P7A_ALL)" "8 loop-CLI files: PushNotification append line structurally inside runtime prompt value (assign-span byte-identical to HEAD, launch-line content matches known-good pre-P7a text, line numbers re-derived at implementation time per FIND-006/FIND-007)"

# ---------------------------------------------------------------------------
# PROP-P7b — REQ-P7b: wording fidelity of the 8 append lines — Tier 2, adversary-only
# ---------------------------------------------------------------------------
report PROP-P7b SKIP "tier-2: manual — fresh-context adversary confirms wording fidelity of the 8 append lines + position double-check"

# ---------------------------------------------------------------------------
# PROP-P7c — REQ-P7c: live PushNotification send E2E — Tier 2, main-agent-only, no mock
# ---------------------------------------------------------------------------
report PROP-P7c SKIP "tier-2: manual E2E — main agent spawns claude -p --model sonnet and captures a real PushNotification tool_result (task #6)"

# ---------------------------------------------------------------------------
# PROP-P8 — REQ-P8: superpowers hooks.json SessionStart entry removed
# ---------------------------------------------------------------------------
p8_check() {
  local HJ="${HOME}/.claude/plugins/cache/superpowers-marketplace/superpowers/5.0.7/hooks/hooks.json"
  [ -f "$HJ" ] || return 1
  jq -e '[(.hooks.SessionStart // []) | .[].hooks[]?.command | select(test("session-start"))] | length == 0' "$HJ" >/dev/null 2>&1 || return 1
  jq . "$HJ" >/dev/null 2>&1 || return 1
  local backup="${BACKUP_DIR}/hooks.json"
  [ -f "$backup" ] || return 1
  diff <(jq -S 'del(.hooks.SessionStart)' "$backup" 2>/dev/null) <(jq -S 'del(.hooks.SessionStart)' "$HJ" 2>/dev/null) >/dev/null 2>&1
}
p8_check; report PROP-P8 "$(as_status $?)" "superpowers hooks.json: SessionStart using-superpowers entry removed, valid JSON, other hooks unchanged vs backup"

# ---------------------------------------------------------------------------
# PROP-SAFE-1 — REQ-SAFE-1: 6 pre-edit backups exist, timestamped before their edit
#   NOTE (implementation note, not a spec deviation): ~/.claude/settings.json and this worktree's
#   .claude/settings.json share the basename "settings.json" and cannot both be backed up under
#   the literal same path; this script expects the worktree copy's backup to be distinguishable
#   as "settings.json.worktree" so both backups can coexist (see report to team-lead).
# ---------------------------------------------------------------------------
safe1_one() {
  # args: original_path backup_basename
  local orig="$1" backup_base="$2"
  local backup="${BACKUP_DIR}/${backup_base}"
  [ -f "$backup" ] || return 1
  if [ -f "$orig" ]; then
    local bt ot
    bt=$(stat -f %m "$backup" 2>/dev/null || stat -c %Y "$backup" 2>/dev/null)
    ot=$(stat -f %m "$orig" 2>/dev/null || stat -c %Y "$orig" 2>/dev/null)
    [ -n "$bt" ] && [ -n "$ot" ] && [ "$bt" -le "$ot" ]
  else
    # file was deleted (e.g. loop-engineering.md) — backup existing is sufficient
    return 0
  fi
}
SAFE1_ALL=0
safe1_one "${HOME}/.claude/plugins/cache/ww-w-ai/claude-code-token-saver/2.1.0/hooks/git-context-lite.sh" "git-context-lite.sh" || SAFE1_ALL=1
safe1_one "${HOME}/.claude/rules/loop-engineering.md" "loop-engineering.md" || SAFE1_ALL=1
safe1_one "${HOME}/.claude/plugins/cache/ww-w-ai/claude-code-token-saver/2.1.0/hooks/session-architecture.md" "session-architecture.md" || SAFE1_ALL=1
safe1_one "${HOME}/.claude/settings.json" "settings.json" || SAFE1_ALL=1
safe1_one "${ROOT_DIR}/.claude/settings.json" "settings.json.worktree" || SAFE1_ALL=1
safe1_one "${HOME}/.claude/plugins/cache/superpowers-marketplace/superpowers/5.0.7/hooks/hooks.json" "hooks.json" || SAFE1_ALL=1
report PROP-SAFE-1 "$(as_status $SAFE1_ALL)" "6 pre-edit backups exist under ${BACKUP_DIR}, timestamped before their edit"

# ---------------------------------------------------------------------------
# PROP-SAFE-2 — REQ-SAFE-2: 4 JSON files remain jq-parseable
# ---------------------------------------------------------------------------
safe2_check() {
  jq . "${HOME}/.claude/settings.json" >/dev/null 2>&1 \
    && jq . "${ROOT_DIR}/.claude/settings.json" >/dev/null 2>&1 \
    && jq . "${LIVE_CHECKOUT}/.claude/settings.json" >/dev/null 2>&1 \
    && jq . "${HOME}/.claude/plugins/cache/superpowers-marketplace/superpowers/5.0.7/hooks/hooks.json" >/dev/null 2>&1
}
safe2_check; report PROP-SAFE-2 "$(as_status $?)" "settings.json (x2) + hooks.json all valid JSON (this invariant holds before AND after implementation, so a pre-implementation PASS here is expected, not a weak-assertion signal)"

# ---------------------------------------------------------------------------
# PROP-SAFE-3 — REQ-SAFE-3: cozempic hooks / enabledPlugins / includeGitInstructions / context7.md
#   unchanged across the whole feature.
#   "pre" reference for the settings.json-derived invariants = the REQ-SAFE-1 backup
#   (~/.claude is not a git repo, so the backup is the only pre-edit reference point).
#   context7.md is never an edit target of this feature; its known-good md5 was captured at
#   Phase 2a authoring time (2026-07-07, before any implementation edit) and is hardcoded below —
#   this keeps the running script itself read-only while still giving a real, falsifiable check.
# ---------------------------------------------------------------------------
CONTEXT7_MD5_BASELINE="2db89435c3fa9d16dc02322b67535cd8"

safe3_check() {
  local backup="${BACKUP_DIR}/settings.json"
  local live="${HOME}/.claude/settings.json"
  [ -f "$backup" ] || return 1

  diff <(jq -S '.enabledPlugins' "$backup" 2>/dev/null) <(jq -S '.enabledPlugins' "$live" 2>/dev/null) >/dev/null 2>&1 || return 1
  diff <(jq -S '.includeGitInstructions' "$backup" 2>/dev/null) <(jq -S '.includeGitInstructions' "$live" 2>/dev/null) >/dev/null 2>&1 || return 1

  local pre_cozempic post_cozempic
  pre_cozempic=$(jq -c '[.hooks | to_entries[]? | .value[]? | .hooks[]?.command | select(test("cozempic"))] | sort' "$backup" 2>/dev/null)
  post_cozempic=$(jq -c '[.hooks | to_entries[]? | .value[]? | .hooks[]?.command | select(test("cozempic"))] | sort' "$live" 2>/dev/null)
  [ -n "$pre_cozempic" ] && [ "$pre_cozempic" = "$post_cozempic" ] || return 1

  local context7="${HOME}/.claude/rules/context7.md"
  [ -f "$context7" ] || return 1
  local current_md5
  current_md5=$(md5sum "$context7" 2>/dev/null | awk '{print $1}')
  [ -z "$current_md5" ] && current_md5=$(md5 -q "$context7" 2>/dev/null)
  [ "$current_md5" = "$CONTEXT7_MD5_BASELINE" ]
}
safe3_check; report PROP-SAFE-3 "$(as_status $?)" "cozempic hooks / enabledPlugins / includeGitInstructions unchanged (backup vs live), context7.md md5 matches 2026-07-07 baseline"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "---"
echo "TOTAL: ${PASS_COUNT} PASS / ${FAIL_COUNT} FAIL (${SKIP_COUNT} SKIP, tier-2, not counted)"

if [ "$FAIL_COUNT" -gt 0 ]; then
  exit 1
fi
exit 0
