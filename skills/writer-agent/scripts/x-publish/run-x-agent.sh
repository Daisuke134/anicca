#!/bin/bash
# A2 — run the headless X-Article agent: take an article → draft → VISION verify → (publish if AUTONOMY=on).
# The agent prompt is x-agent-prompt.md. Spec: docs/superpowers/specs/2026-06-25-publish-verify-prompts-A2A3.md.
# Usage: run-x-agent.sh --md <markdown>   (AUTONOMY defaults off = stop at draft for review; AUTONOMY=on to auto-publish)
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT="$DIR/x-agent-prompt.md"
MODEL_RUNNER="${ARTICLE_MODEL_RUNNER:-$HOME/profitable-claude/skills/writer-agent/runtime/model-runner.sh}"
AUTONOMY="${AUTONOMY:-off}"
MD=""
while [ $# -gt 0 ]; do case "$1" in
  --md) MD="$2"; shift 2;;
  *) echo "unknown arg: $1"; exit 2;;
esac; done
[ -f "$MD" ] || { echo "md not found: $MD"; exit 2; }
INPUTS="INPUTS: MD=\"$MD\" AUTONOMY=\"$AUTONOMY\""
FULL="$(cat "$PROMPT")
$INPUTS"

printf '%s' "$FULL" | "$MODEL_RUNNER" agent --prompt-file -
