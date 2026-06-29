#!/usr/bin/env bash
# llm-call.sh — MODEL-AGNOSTIC chat completion. The skill NEVER hardcodes a provider/model:
# each agent uses ITS OWN model (OpenClaw→DeepSeek, Claude→Claude, others→theirs). The
# ENVIRONMENT decides, not this code.
#
# Resolution order (first that resolves wins):
#   1) explicit override:  LLM_API_BASE + LLM_API_KEY + LLM_MODEL   (any OpenAI-compatible endpoint)
#   2) Anthropic native:   ANTHROPIC_API_KEY (+ optional ANTHROPIC_MODEL)
#   3) auto-detect a known key: DEEPSEEK / OPENAI / OPENROUTER / GROQ / TOGETHER  (OpenAI-compatible)
# Input  (env): SYS (system prompt), USERP (user prompt), optional LLM_TEMPERATURE (default 0.9).
# Output: assistant message text to stdout. Exit 5 if no LLM is configured.
set -euo pipefail
: "${SYS:?SYS env required}"; : "${USERP:?USERP env required}"
TEMP="${LLM_TEMPERATURE:-0.9}"
BASE="${LLM_API_BASE:-}"; KEY="${LLM_API_KEY:-}"; MODEL="${LLM_MODEL:-}"

# Anthropic native (different API shape) — only when explicitly Anthropic and no OpenAI-compat override
if [ -z "$BASE" ] && [ -z "$KEY" ] && [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  AMODEL="${ANTHROPIC_MODEL:-${LLM_MODEL:-claude-sonnet-4-6}}"
  RESP="$(SYS="$SYS" USERP="$USERP" AMODEL="$AMODEL" TEMP="$TEMP" python3 -c "import json,os;print(json.dumps({'model':os.environ['AMODEL'],'max_tokens':1024,'temperature':float(os.environ['TEMP']),'system':os.environ['SYS'],'messages':[{'role':'user','content':os.environ['USERP']}]}))" \
    | curl -sS https://api.anthropic.com/v1/messages -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" -H "Content-Type: application/json" -d @-)"
  printf '%s' "$RESP" | python3 -c "import json,sys;d=json.load(sys.stdin);print(''.join(b.get('text','') for b in d['content']).strip())"
  exit 0
fi

# OpenAI-compatible (explicit override OR auto-detect)
if [ -z "$BASE" ] || [ -z "$KEY" ]; then
  if   [ -n "${DEEPSEEK_API_KEY:-}" ];   then BASE="https://api.deepseek.com";            KEY="$DEEPSEEK_API_KEY";   MODEL="${MODEL:-deepseek-chat}"
  elif [ -n "${OPENAI_API_KEY:-}" ];     then BASE="https://api.openai.com/v1";           KEY="$OPENAI_API_KEY";     MODEL="${MODEL:-gpt-4o-mini}"
  elif [ -n "${OPENROUTER_API_KEY:-}" ]; then BASE="https://openrouter.ai/api/v1";        KEY="$OPENROUTER_API_KEY"; MODEL="${MODEL:-openai/gpt-4o-mini}"
  elif [ -n "${GROQ_API_KEY:-}" ];       then BASE="https://api.groq.com/openai/v1";      KEY="$GROQ_API_KEY";       MODEL="${MODEL:-llama-3.3-70b-versatile}"
  elif [ -n "${TOGETHER_API_KEY:-}" ];   then BASE="https://api.together.xyz/v1";          KEY="$TOGETHER_API_KEY";   MODEL="${MODEL:-meta-llama/Llama-3.3-70B-Instruct-Turbo}"
  else echo "LLM_NOT_CONFIGURED: set LLM_API_BASE+LLM_API_KEY+LLM_MODEL (any OpenAI-compatible) or ANTHROPIC_API_KEY or a known *_API_KEY" >&2; exit 5; fi
fi
[ -n "$MODEL" ] || { echo "LLM_MODEL not set for custom LLM_API_BASE" >&2; exit 5; }

PAYLOAD="$(SYS="$SYS" USERP="$USERP" MODEL="$MODEL" TEMP="$TEMP" python3 -c "import json,os;print(json.dumps({'model':os.environ['MODEL'],'messages':[{'role':'system','content':os.environ['SYS']},{'role':'user','content':os.environ['USERP']}],'temperature':float(os.environ['TEMP'])}))")"
RESP="$(curl -sS "${BASE%/}/chat/completions" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d "$PAYLOAD")"
printf '%s' "$RESP" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['choices'][0]['message']['content'].strip())"
