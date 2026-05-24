#!/usr/bin/env bash
# set-env.sh — the ONLY writer of $ANICCA_HOME/.env (secrets).
# Upserts KEY=VALUE (no duplicates), keeps file 0600, never echoes the value.
# Usage: bash set-env.sh KEY "value"
set -euo pipefail
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
ENV_FILE="$ANICCA_HOME/.env"
KEY="${1:?usage: set-env.sh KEY VALUE}"; VAL="${2:?usage: set-env.sh KEY VALUE}"
[[ "$KEY" =~ ^[A-Z_][A-Z0-9_]*$ ]] || { echo "❌ bad key name: $KEY" >&2; exit 1; }
touch "$ENV_FILE"; chmod 600 "$ENV_FILE"
tmp="$(mktemp)"
# drop existing line(s) for KEY, then append the new one
grep -vE "^${KEY}=" "$ENV_FILE" > "$tmp" || true
printf '%s=%s\n' "$KEY" "$VAL" >> "$tmp"
chmod 600 "$tmp"; mv "$tmp" "$ENV_FILE"
echo "✅ set $KEY in .env (value hidden)"
