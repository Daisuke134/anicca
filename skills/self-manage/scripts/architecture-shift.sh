#!/usr/bin/env bash
# architecture-shift: BIG self-changes (skill add/delete/merge) that require a multi-instance
# vote via the forum (spec 18 §2 ROLLOUT). Real execution depends on #338 vote integration.
#
# Wave 1: file the proposal as a forum issue (@anicca [arch-shift]) + log FILED. The vote
# wiring is tracked as follow-on #336b-architecture-vote-integration.
#
# Usage:
#   architecture-shift.sh ['{"type":"arch-shift","title":"merge X+Y","body":"...","reason":"..."}']
#
# Env:
#   DRY_RUN=1   guard-check + print intended issue title only; no gh write.
#
# Exit: 0 filed (or dry-run pass), non-zero on block/error.
set -uo pipefail
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$SCRIPTS/_lib.sh"

prop="${1:-}"
[ -z "$prop" ] && prop="$(sm_latest_unresolved arch-shift)"
if [ -z "$prop" ]; then
  echo "architecture-shift: no proposal supplied and no unresolved arch-shift proposal queued" >&2
  exit 0
fi

title="$(printf '%s' "$prop" | "$JQ" -r '.title // empty')"
body="$(printf '%s' "$prop" | "$JQ" -r '.body // ""')"
reason="$(printf '%s' "$prop" | "$JQ" -r '.reason // "(no reason)"')"
id="$(sm_id "$prop")"

if [ -z "$title" ]; then
  echo "architecture-shift: proposal missing .title" >&2
  sm_log "$id" arch-shift ERROR "missing title field"
  exit 1
fi

intent="Propose an architecture shift to the swarm: '$title'. Reason: $reason. This is filed as a forum proposal for a multi-instance vote; it does not itself modify the North Star, Law I, or the Constitution."

if ! sm_guard "$intent"; then
  rc=$?
  echo "architecture-shift: BLOCKED by constitution-guard (exit $rc)" >&2
  sm_log "$id" arch-shift BLOCKED "guard exit $rc: $title"
  exit 2
fi

issue_title="@anicca [arch-shift]: $title"
issue_body="$(printf '**Architecture-shift proposal** (self-manage #336, Wave 1 = vote pending #338).\n\n**Reason:** %s\n\n%s\n\n@anicca instances: vote here. Real execution is gated on the multi-instance vote integration (#336b).\n\nFiled by skills/self-manage/scripts/architecture-shift.sh' "$reason" "$body")"

if [ "${DRY_RUN:-}" = "1" ]; then
  echo "architecture-shift: DRY_RUN guard PASS — would file: $issue_title"
  exit 0
fi

url="$(gh issue create --repo "$FORUM_REPO" --title "$issue_title" --body "$issue_body" \
        --label arch-shift 2>/dev/null)"
if [ -z "$url" ]; then
  # label may not exist — retry without it so the proposal is never lost
  url="$(gh issue create --repo "$FORUM_REPO" --title "$issue_title" --body "$issue_body" 2>/dev/null)" || url=""
fi

if [ -n "$url" ]; then
  echo "architecture-shift: FILED $url"
  sm_log "$id" arch-shift FILED "$url"
  exit 0
fi

echo "architecture-shift: gh issue create failed" >&2
sm_log "$id" arch-shift ERROR "gh issue create failed: $title"
exit 1
