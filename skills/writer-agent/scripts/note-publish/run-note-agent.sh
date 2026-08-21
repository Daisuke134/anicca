#!/bin/bash
# F2 — run the headless note agent: write/take an article → draft → VISION verify → (go if AUTONOMY=on).
# The agent prompt is note-agent-prompt.md. Spec: docs/superpowers/specs/2026-06-24-note-agent-F2.md.
# Usage:
#   run-note-agent.sh --md <markdown> --key <noteKey> [--price 500] [--paywall-before "H"] [--eyecatch IMG]
#   run-note-agent.sh --topic "<topic>" [...]
#   AUTONOMY defaults to off (stop at draft for review). Set AUTONOMY=on to allow auto-publish once the
#   vision checklist passes. (Dais's "prepare the tap, don't tap yet" — keep off until the skill is proven.)
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT="$DIR/note-agent-prompt.md"
MODEL_RUNNER="${ARTICLE_MODEL_RUNNER:-${ARTICLE_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)}/runtime/model-runner.sh}"
AUTONOMY="${AUTONOMY:-off}"
TOPIC=""; MD=""; KEY="new"; PRICE="500"; PAYWALL=""; EYECATCH=""
while [ $# -gt 0 ]; do case "$1" in
  --topic) TOPIC="$2"; shift 2;;
  --md) MD="$2"; shift 2;;
  --key) KEY="$2"; shift 2;;
  --price) PRICE="$2"; shift 2;;
  --paywall-before) PAYWALL="$2"; shift 2;;
  --eyecatch) EYECATCH="$2"; shift 2;;
  *) echo "unknown arg: $1"; exit 2;;
esac; done

INPUTS="INPUTS: TOPIC=\"$TOPIC\" MD=\"$MD\" NOTE_KEY=\"$KEY\" PRICE=\"$PRICE\" PAYWALL_BEFORE=\"$PAYWALL\" EYECATCH=\"$EYECATCH\" AUTONOMY=\"$AUTONOMY\""
FULL="$(cat "$PROMPT")
$INPUTS"

printf '%s' "$FULL" | "$MODEL_RUNNER" agent --prompt-file -
