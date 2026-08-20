#!/usr/bin/env bash
# SSOT §9.3.1 item H2, wired. One bounded repair attempt per run, for the one
# incident a completed investigation has already handed to this stage.
#
# This worker deliberately does NOT do three things, and each omission is what
# makes the placement safe:
#
#   1. it never takes the lock the daily creator and the resume tick share, so
#      a 900-second repair cannot delay or starve a 300-second recovery tick,
#      the zenn retry worker, or the 06:00 creator;
#   2. it never creates a run and never performs a shipment, so R6's "exactly
#      one daily creator, exactly one same-run recovery owner" still holds --
#      this label is neither;
#   3. it never loads the runtime credential file, so no destination secret is
#      even present in this process, let alone in the model child.
#
# Deploying the candidate, resuming the work item and the public readback are
# Order 5 and are not performed here. This script stops at a registered
# verified candidate.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"

ARTICLE_ROOT="${ARTICLE_ROOT:-$HOME/profitable-claude/skills/writer-agent}"
STATE_DIR="${ARTICLE_STATE_DIR:-$ARTICLE_ROOT/state}"
LOG="${ARTICLE_REPAIR_LOG:-$HOME/.openclaw/logs/article-repair-candidate.log}"
MODEL_RUNNER="${ARTICLE_MODEL_RUNNER:-$ARTICLE_ROOT/runtime/model-runner.sh}"
BASE_REF="${ARTICLE_REPAIR_BASE_REF:-HEAD}"
# Candidate worktrees live outside the repository on purpose: regenerable, and
# incapable of showing up in the source tree's own porcelain status.
REPAIR_ROOT="${ARTICLE_REPAIR_ROOT:-$HOME/.cache/anicca-writer-repair}"

mkdir -p "$(dirname "$LOG")"

QUEUE="$STATE_DIR/self-heal/incident-queue.json"
[ -f "$QUEUE" ] || exit 0

REPO="${ARTICLE_REPAIR_REPO:-$(git -C "$ARTICLE_ROOT" rev-parse --show-toplevel 2>/dev/null || true)}"
if [ -z "$REPO" ]; then
  echo "article-repair-candidate: no git checkout above $ARTICLE_ROOT" >>"$LOG"
  exit 0
fi

python3 "$ARTICLE_ROOT/scripts/writer_repair_candidate_dispatch.py" \
  --state-root "$STATE_DIR" \
  --repo "$REPO" \
  --base-ref "$BASE_REF" \
  --repair-root "$REPAIR_ROOT" \
  --model-runner "$MODEL_RUNNER" \
  --observed-at "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  >>"$LOG" 2>&1 \
  || echo "article-repair-candidate: repair channel failed closed" >>"$LOG"

exit 0
