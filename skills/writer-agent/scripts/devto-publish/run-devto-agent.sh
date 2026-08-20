#!/bin/bash
# A4 — run the headless dev.to agent: English article → publish → MANDATORY browser-verify → unpublish+fix
# if any image is broken → repeat until clean. Prompt = devto-agent-prompt.md. NO human in the loop.
# Usage: run-devto-agent.sh --md <english-markdown>   (AUTONOMY defaults on for dev.to: it self-verifies + unpublishes
#        on failure, so auto-publish is safe — the browser gate is what guards quality.)
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT="$DIR/devto-agent-prompt.md"
MODEL_RUNNER="${ARTICLE_MODEL_RUNNER:-$HOME/profitable-claude/skills/article-writer/runtime/model-runner.sh}"
AUTONOMY="${AUTONOMY:-on}"
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
