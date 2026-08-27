#!/usr/bin/env bash
# Render one managed Larry account config into the shared creative/posting prompt.
set -euo pipefail

ACCOUNT_KEY=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --account-key) ACCOUNT_KEY="${2:-}"; shift 2 ;;
    *) echo "run_larry_fixed_strings.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ "$ACCOUNT_KEY" =~ ^[A-Za-z0-9._-]+$ ]] || {
  echo "run_larry_fixed_strings.sh: invalid or missing --account-key" >&2
  exit 2
}

CONFIG="${LARRY_ACCOUNT_CONFIG:-/Users/anicca/profitable-claude/config/openclaw/larry-fixed-strings.json}"
TEMPLATE="${LARRY_PROMPT_TEMPLATE:-/Users/anicca/profitable-claude/config/openclaw/prompts/larry-fixed-strings.md}"
MARKETING_RUNNER="${LARRY_MARKETING_RUNNER:-/Users/anicca/profitable-claude/bin/run_marketing_prompt.sh}"
[ -f "$CONFIG" ] || { echo "run_larry_fixed_strings.sh: config not found: $CONFIG" >&2; exit 2; }
[ -f "$TEMPLATE" ] || { echo "run_larry_fixed_strings.sh: template not found: $TEMPLATE" >&2; exit 2; }
[ -x "$MARKETING_RUNNER" ] || { echo "run_larry_fixed_strings.sh: runner not executable: $MARKETING_RUNNER" >&2; exit 2; }

ACCOUNT_JSON="$(jq -c --arg key "$ACCOUNT_KEY" '.accounts[$key] // null' "$CONFIG")"
[ "$ACCOUNT_JSON" != "null" ] || {
  echo "run_larry_fixed_strings.sh: unknown account key: $ACCOUNT_KEY" >&2
  exit 2
}
jq -e '
  (.task_label | type == "string" and length > 0) and
  (.language | type == "string" and length > 0) and
  (.history_account | type == "string" and length > 0) and
  (.history_prefixes | type == "array" and length > 0 and all(.[]; type == "string" and length > 0)) and
  (.fixed_strings | type == "string" and length > 0) and
  (.pattern_library | type == "string" and length > 0) and
  (.history_library | type == "string" and length > 0) and
  (.tiktok_connection | type == "string" and length > 0) and
  ((.instagram_connection == null) or (.instagram_connection | type == "string" and length > 0)) and
  (.run_slug | type == "string" and length > 0)
' >/dev/null <<<"$ACCOUNT_JSON" || {
  echo "run_larry_fixed_strings.sh: incomplete account config: $ACCOUNT_KEY" >&2
  exit 2
}

TASK_LABEL="$(jq -r '.task_label' <<<"$ACCOUNT_JSON")"
[[ "$TASK_LABEL" =~ ^[A-Za-z0-9._-]+$ ]] || {
  echo "run_larry_fixed_strings.sh: unsafe task_label in config" >&2
  exit 2
}

PROMPT_FILE="$(mktemp "${TMPDIR:-/tmp}/larry-fixed-strings.XXXXXX")"
trap 'rm -f "$PROMPT_FILE"' EXIT
{
  printf 'ACCOUNT CONFIG (authoritative, managed JSON):\n'
  jq . <<<"$ACCOUNT_JSON"
  printf '\n'
  cat "$TEMPLATE"
} >"$PROMPT_FILE"

"$MARKETING_RUNNER" \
  --label "$TASK_LABEL" \
  --prompt "$PROMPT_FILE" \
  --workdir /Users/anicca/.openclaw
