#!/usr/bin/env bash
# HARD RULE 0.32 + 0.33 systemization
# Injected on SessionStart + UserPromptSubmit to enforce spec+tasklist SSOT discipline
TASKLIST_DIR=~/.claude/tasks
PROJECT_DIR=/Users/anicca/anicca-project

# Count pending tasks
PENDING_COUNT=0
if [ -d "$TASKLIST_DIR" ]; then
  PENDING_COUNT=$(find "$TASKLIST_DIR" -name "*.json" 2>/dev/null | xargs grep -l '"status":"pending"' 2>/dev/null | wc -l | tr -d ' ')
fi

# Latest spec file
LATEST_SPEC=$(ls -t "$PROJECT_DIR/docs/superpowers/specs/"*.md 2>/dev/null | head -1)
SPEC_BASE=$(basename "$LATEST_SPEC" 2>/dev/null)

cat <<EOF
=== SSOT GUARD (= HARD RULE 0.32 + 0.33 systemized) ===
Pending tasks: $PENDING_COUNT (= TaskList tool で全 表示、 必ず order 順 work)
Latest spec: $SPEC_BASE
Reminders:
  ★ Per HARD RULE 0.33: ★ Dais 待ち = 罪 ★ — work exists = immediate execute
  ★ Per HARD RULE 0.32: ★ task 確定 = 即 TaskCreate、 状態変化 = 即 TaskUpdate、 spec 変更 = 即 commit+push、 permission ゼロ ★
  ★ Per HARD RULE 0.31: ★ E2E verify = MD5 + frame + audio + Postiz URL まで、 patch だけ で完了報告 = 大罪 ★
EOF
