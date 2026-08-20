#!/bin/bash
# A2 — run the headless Substack agent: article → draft (free explainer + paywall + paid) → VISION verify
# → (publish if AUTONOMY=on). Prompt = substack-agent-prompt.md. AUTONOMY defaults off (stop at draft).
# Usage: run-substack-agent.sh --md <md> --title "<title>" --paid-from "<heading>"
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT="$DIR/substack-agent-prompt.md"
MODEL_RUNNER="${ARTICLE_MODEL_RUNNER:-${ARTICLE_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)}/runtime/model-runner.sh}"
AUTONOMY="${AUTONOMY:-off}"
MD=""; TITLE=""; PAID_FROM="実際に動かす"
while [ $# -gt 0 ]; do case "$1" in
  --md) MD="$2"; shift 2;;
  --title) TITLE="$2"; shift 2;;
  --paid-from) PAID_FROM="$2"; shift 2;;
  *) echo "unknown arg: $1"; exit 2;;
esac; done
[ -f "$MD" ] || { echo "md not found: $MD"; exit 2; }
INPUTS="INPUTS: MD=\"$MD\" TITLE=\"$TITLE\" PAID_FROM=\"$PAID_FROM\" AUTONOMY=\"$AUTONOMY\""
FULL="$(cat "$PROMPT")
$INPUTS"

printf '%s' "$FULL" | "$MODEL_RUNNER" agent --prompt-file -
