#!/bin/bash
# A2 — run the headless Zenn agent: article → adapt+draft (free explainer) → no-lie gate → render VISION
# verify → (publish if AUTONOMY=on). Prompt = zenn-agent-prompt.md. AUTONOMY defaults off (stop at draft).
# Usage: run-zenn-agent.sh --md <md> --paid-from "<heading>" --slug "<a-z0-9 slug>"
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT="$DIR/zenn-agent-prompt.md"
MODEL_RUNNER="${ARTICLE_MODEL_RUNNER:-$HOME/profitable-claude/skills/article-writer/runtime/model-runner.sh}"
AUTONOMY="${AUTONOMY:-off}"
MD=""; PAID_FROM="実際に動かす"; SLUG=""
while [ $# -gt 0 ]; do case "$1" in
  --md) MD="$2"; shift 2;;
  --paid-from) PAID_FROM="$2"; shift 2;;
  --slug) SLUG="$2"; shift 2;;
  *) echo "unknown arg: $1"; exit 2;;
esac; done
[ -f "$MD" ] || { echo "md not found: $MD"; exit 2; }
INPUTS="INPUTS: MD=\"$MD\" PAID_FROM=\"$PAID_FROM\" SLUG=\"$SLUG\" AUTONOMY=\"$AUTONOMY\""
FULL="$(cat "$PROMPT")
$INPUTS"

printf '%s' "$FULL" | "$MODEL_RUNNER" agent --prompt-file -
