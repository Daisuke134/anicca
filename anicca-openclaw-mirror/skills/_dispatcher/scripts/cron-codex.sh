#!/usr/bin/env bash
# Rat-proof cron entrypoint (Path 2 — codex exec non-interactive agent).
#
# Usage:
#   cron-codex.sh <skill-name> [extra prompt text...]
#   cron-codex.sh anicca-earn-bounty
#   cron-codex.sh anicca-mail-triage "today only"
#
# Spawns `codex exec` headless agent with full Codex tool stack + MCP plugins
# per ~/.codex/config.toml. The agent reads the named skill's SKILL.md and
# runs its canonical entrypoint.

set -uo pipefail

# Anicca v3.2 routing context flag (Plan ③). No active consumer today; future
# router infra (or skill-side judgments) can branch on this to pick cheap
# defaults vs frontier models. Counterpart in phone autostart sets
# OPENCLAW_CONTEXT=interactive — see ~/.zshrc.
export OPENCLAW_CONTEXT=cron

SKILL="${1:?usage: cron-codex.sh <skill-name> [extra prompt...]}"; shift || true
EXTRA="$*"
SKILL_DIR="$HOME/.openclaw/skills/$SKILL"

if [ ! -d "$SKILL_DIR" ]; then
    echo ":x: cron-codex: skill dir not found: $SKILL_DIR" >&2
    exit 2
fi

set -a
. "$HOME/.openclaw/.env" 2>/dev/null || true
set +a

# Ensure codex exec sees OpenAI auth when invoked from inside OpenClaw's
# isolated sandbox (which strips env). 401 Unauthorized observed
# 2026-06-04 12:37 without this. ~/.codex/auth.json carries the user's
# canonical token; both paths combined make it bullet-proof.
export CODEX_HOME="$HOME/.codex"
[ -z "${OPENAI_API_KEY:-}" ] && [ -f "$CODEX_HOME/auth.json" ] && \
    OPENAI_API_KEY="$(python3 -c "import json; print(json.load(open('$CODEX_HOME/auth.json')).get('OPENAI_API_KEY',''))" 2>/dev/null)" && \
    export OPENAI_API_KEY

# R-8 token budget guard. Reads OPENAI_MONTHLY_BUDGET_USD (default $50)
# and the doctor's accumulated spend file. Exits 0 cleanly if budget
# would be exceeded after this run.
BUDGET_PATH="$HOME/.openclaw/skills/anicca-cron-doctor/data/openai-spend.json"
MONTHLY="${OPENAI_MONTHLY_BUDGET_USD:-50.0}"
CRON_DOCTOR_SCRIPTS="$HOME/.openclaw/skills/anicca-cron-doctor/scripts"
if [ -d "$CRON_DOCTOR_SCRIPTS/helpers" ]; then
    BUDGET_RC=0
    BUDGET_INFO="$(python3 - "$BUDGET_PATH" "$MONTHLY" "$SKILL" <<'PY' 2>/dev/null
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path.home() / ".openclaw/skills/anicca-cron-doctor/scripts"))
from helpers.token_budget import check_budget
ok, info = check_budget(sys.argv[1], float(sys.argv[2]), 80_000, "gpt-5.4-mini")
print(json.dumps(info))
sys.exit(0 if ok else 1)
PY
)" || BUDGET_RC=$?
    if [ "$BUDGET_RC" != "0" ]; then
        MSG=":money_with_wings: skipped \`${SKILL}\`: monthly OpenAI budget threshold exceeded — ${BUDGET_INFO}"
        echo "$MSG"
        if [ -n "${SLACK_BOT_TOKEN:-}" ]; then
            CHAN="${SLACK_METRICS_CHANNEL:-C091G3PKHL2}"
            PAYLOAD="$(jq -nc --arg c "$CHAN" --arg t "$MSG" '{channel: $c, text: $t}')"
            curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
                -H 'Content-Type: application/json; charset=utf-8' \
                --data "$PAYLOAD" \
                https://slack.com/api/chat.postMessage \
                >/dev/null 2>&1 || true
        fi
        exit 0
    fi
fi

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
LOG="$(mktemp -t cron-codex.XXXXXX.log)"

PROMPT="Read $SKILL_DIR/SKILL.md and execute the cron's canonical bash entrypoint per that skill's instructions. ${EXTRA}

MUST: actually invoke exec_command for any bash you decide to run. Do not return a refusal saying shell/MCP is unavailable — the codex exec sandbox has full shell access (-s danger-full-access). Report stdout tail on success, stderr verbatim on failure."

# codex exec with full sandbox + all MCP plugins
if timeout 1500 codex exec \
    --skip-git-repo-check \
    -s danger-full-access \
    --dangerously-bypass-approvals-and-sandbox \
    --cd "$SKILL_DIR" \
    "$PROMPT" \
    >"$LOG" 2>&1
then
    EXIT=0
    HEAD=":white_check_mark: \`${SKILL}\` ok @ ${TS}"
else
    EXIT=$?
    HEAD=":x: \`${SKILL}\` failed exit=${EXIT} @ ${TS}"
fi

BODY="$(tail -c 2500 "$LOG")"
MSG="${HEAD}"$'\n```\n'"${BODY}"$'\n```'
echo "${MSG}"

CHAN="${SLACK_METRICS_CHANNEL:-C091G3PKHL2}"
if [ -n "${SLACK_BOT_TOKEN:-}" ]; then
    PAYLOAD="$(jq -nc --arg c "${CHAN}" --arg t "${MSG}" '{channel: $c, text: $t}')"
    curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
        -H 'Content-Type: application/json; charset=utf-8' \
        --data "${PAYLOAD}" \
        https://slack.com/api/chat.postMessage \
        >/dev/null 2>&1 || true
elif [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    PAYLOAD="$(jq -nc --arg t "${MSG}" '{text: $t}')"
    curl -sS -X POST -H 'Content-Type: application/json' \
        --data "${PAYLOAD}" \
        "${SLACK_WEBHOOK_URL}" \
        >/dev/null 2>&1 || true
fi

rm -f "$LOG"
exit "${EXIT}"
