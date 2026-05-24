#!/usr/bin/env bash
# scripts/lib/ledger.sh
#
# Local ledger append + anicca-products dashboard.json patch + git push.
# This is the write-back path that triggers the Netlify rebuild of
# aniccaai.com/donation.
#
# Source from install.sh / monthly.sh:
#   source "$(dirname "$0")/lib/ledger.sh"
#
# Functions:
#   ledger_append_local <ledger-entry-json>
#   ledger_patch_dashboard <ledger-entry-json> <next-month-this-month-json>
#   ledger_commit_push <month> <amount> <charity>
# Each function prints LG:<status> lines.

set -uo pipefail

PRODUCTS_DIR="${ANICCA_PRODUCTS_DIR:-$HOME/anicca-products}"
DASHBOARD_PATH="apps/landing/public/dashboard.json"
GIT_BRANCH="${GIT_PUSH_BRANCH:-dev}"
LOCAL_LEDGER="${DONATION_LEDGER:-$HOME/.openclaw/state/donation-ledger.jsonl}"
HISTORY="${DONATION_HISTORY:-$HOME/.openclaw/state/donation-history.jsonl}"

mkdir -p "$(dirname "$LOCAL_LEDGER")"

# ledger_append_local <entry-json>  — append one line to local ledger.jsonl
ledger_append_local() {
  local entry="$1"
  echo "$entry" | jq -c . >> "$LOCAL_LEDGER"
  echo "LG:append_local → $LOCAL_LEDGER"
}

# ledger_append_history <entry-json>
ledger_append_history() {
  local entry="$1"
  echo "$entry" | jq -c . >> "$HISTORY"
  echo "LG:append_history → $HISTORY"
}

# ledger_patch_dashboard <entry-json> <next-month-this-month-json>
#   Patches apps/landing/public/dashboard.json in the local clone.
#   Does NOT commit/push — that's ledger_commit_push.
ledger_patch_dashboard() {
  local entry="$1" next_this_month="$2"
  local dash="$PRODUCTS_DIR/$DASHBOARD_PATH"
  if [ ! -f "$dash" ]; then
    echo "LG:ERR dashboard.json not found at $dash" >&2
    return 1
  fi

  local tmp; tmp="$(mktemp)"
  jq \
    --argjson entry "$entry" \
    --argjson next "$next_this_month" \
    '
    # Initialize .charity if missing
    .charity = (.charity // {ledger: [], total_given_usd: 0, org_count: 0, this_month: null}) |
    .charity.ledger = ((.charity.ledger // []) + [$entry]) |
    .charity.total_given_usd = (
      [.charity.ledger[] | select(.status == "paid") | .amount_usd] | add // 0
    ) |
    .charity.org_count = (
      [.charity.ledger[] | select(.status == "paid") | .charity_name] | unique | length
    ) |
    .charity.this_month = $next |
    .updated_at = (now | todate)
    ' "$dash" > "$tmp"

  if ! jq empty "$tmp" >/dev/null 2>&1; then
    echo "LG:ERR jq merge produced invalid JSON; aborting (kept old $dash)" >&2
    rm -f "$tmp"
    return 1
  fi

  mv "$tmp" "$dash"
  echo "LG:patched $dash"
}

# ledger_commit_push <month> <amount> <charity>
#   git add + commit + push on $GIT_BRANCH. Triggers netlify-deploy.yml.
ledger_commit_push() {
  local month="$1" amount="$2" charity="$3"
  if [ ! -d "$PRODUCTS_DIR/.git" ]; then
    echo "LG:ERR $PRODUCTS_DIR is not a git repo" >&2
    return 1
  fi

  ( cd "$PRODUCTS_DIR" && \
    git fetch origin "$GIT_BRANCH" --quiet && \
    git checkout "$GIT_BRANCH" --quiet && \
    git pull --rebase --quiet origin "$GIT_BRANCH" && \
    git add "$DASHBOARD_PATH" && \
    if git diff --cached --quiet; then
      echo "LG:nochange (dashboard.json unchanged after patch — skipping commit)"
      exit 0
    fi
    git -c user.name="Anicca Donation" -c user.{{profile.lateness.stakeholders.channel}}="{{profile.contact.personalEmail}}" \
      commit -m "chore(donation): refresh ${month} ledger (\$${amount} → ${charity})" --quiet && \
    git push origin "$GIT_BRANCH" --quiet )

  local rc=$?
  if [ $rc -eq 0 ]; then
    local sha
    sha=$( cd "$PRODUCTS_DIR" && git rev-parse --short HEAD )
    echo "LG:committed sha=$sha branch=$GIT_BRANCH"
    echo "LG:netlify rebuild expected within ~3 min"
  else
    echo "LG:ERR git push failed (rc=$rc)" >&2
    return 1
  fi
}

# ledger_dry_preview <entry-json> <next-month-this-month-json>
#   Same as patch + commit but only prints the diff. Used in DRY_RUN.
ledger_dry_preview() {
  local entry="$1" next="$2"
  local dash="$PRODUCTS_DIR/$DASHBOARD_PATH"
  echo "LG:DRY would patch $dash"
  echo "LG:DRY entry → $(echo "$entry" | jq -c .)"
  echo "LG:DRY next this_month → $(echo "$next" | jq -c .)"
  if [ -f "$dash" ]; then
    local existing
    existing=$(jq -c '.charity // null' "$dash")
    echo "LG:DRY existing .charity → $existing"
  fi
  echo "LG:DRY would commit on $GIT_BRANCH and push (no actual commit)"
}
