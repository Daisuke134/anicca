#!/usr/bin/env bash
# Weekly Sunday 03:00 — detect schedule mismatch vs SKILL.md
set -uo pipefail
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
REPO="Daisuke134/anicca-products"

openclaw cron list --all --json 2>/dev/null | jq -c '.jobs[]? | select(.enabled==true)' | while read -r J; do
  NAME=$(echo "$J" | jq -r '.name')
  EXPR=$(echo "$J" | jq -r '.schedule.expr')
  SKILL_MD="$HOME/.openclaw/skills/$NAME/SKILL.md"
  [ ! -f "$SKILL_MD" ] && continue

  # Heuristic: SKILL.md says "daily" but expr is */N hours
  if grep -qiE "daily|once.a.day|nightly" "$SKILL_MD" && \
     echo "$EXPR" | grep -qE "^\*/[1-6] |^0 \*/[1-6] |^0 \* "; then
    EXISTING=$(gh issue list -R "$REPO" --label "cornerstone:infra" \
                 --label "cron:${NAME}" --state open --json number 2>/dev/null | jq -r '.[0].number // empty')
    [ -n "$EXISTING" ] && continue
    gh issue create -R "$REPO" \
      --label "cornerstone:infra" --label "ai-ready" --label "cron:${NAME}" \
      --title "Over-scheduled: $NAME ($EXPR vs daily description)" \
      --body "Schedule '$EXPR' fires more often than SKILL.md suggests. cron-manager will propose schedule edit." 2>&1 | tail -1
  fi
done
exit 0
