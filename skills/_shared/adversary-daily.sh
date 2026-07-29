#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
# adversary-daily.sh — REQ-E1 daily fresh-context Opus adversary review.
# Invoked at 03:00 by launchd plist ai.anicca.<slot>-adversary-daily.
#
# Usage: adversary-daily.sh <slot> [nightly|strategy-mutation <sha>]
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SLOT="${1:-}"
MODE="${2:-nightly}"
EXTRA="${3:-}"
SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_TMPL="${SHARED_DIR}/adversary-daily-prompt.tmpl"
LOG="${HOME}/.openclaw/logs/${SLOT}-adversary-daily.log"
mkdir -p "$(dirname "$LOG")"

# Render prompt by substituting tokens; then invoke `claude -p` as a fresh top-level session.
# That session is responsible for issuing exactly one `Agent` call with
# subagent_type=vcsdd:vcsdd-adversary (= the second fresh context layer).
PROMPT=$(sed -e "s|{{SLOT}}|${SLOT}|g" -e "s|{{MODE}}|${MODE}|g" -e "s|{{EXTRA}}|${EXTRA}|g" "$PROMPT_TMPL" 2>/dev/null || \
         echo "Review feature ${SLOT} per $LIFE_MANAGER_REPO/.vcsdd/features/${SLOT}/specs/ in mode ${MODE}.")
PROMPT="${PROMPT} 検証結果がFAIL verdictだった場合のみ、終了前にPushNotificationツールでDaisへその要点をverbatim送信すること。PASSの場合やnarration・定常報告には使わない。"

claude -p "$PROMPT" --model opus --output-format text 2>&1 | tee -a "$LOG"
