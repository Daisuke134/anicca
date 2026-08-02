#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 0 ]; then
  echo "apply-to-yc compatibility shim requires zero arguments" >&2
  exit 64
fi

CDP_URL="${BU_CDP_URL:-http://127.0.0.1:9222}"
if [ "$CDP_URL" != "http://127.0.0.1:9222" ]; then
  echo "apply-to-yc daily-driver route refused" >&2
  exit 65
fi

if [ -n "${DRAFT_ID:-}" ] || [ -n "${FOUNDER_VIDEO:-}" ] || [ -n "${DEMO_VIDEO:-}" ]; then
  echo "apply-to-yc legacy content override refused" >&2
  exit 66
fi

SUCCESSOR="$HOME/.openclaw/skills/apply-to-funder/scripts/run.sh"
if [ ! -x "$SUCCESSOR" ]; then
  echo "apply-to-yc successor unavailable" >&2
  exit 67
fi

export BU_CDP_URL="http://127.0.0.1:9222"
exec bash "$SUCCESSOR" --funder yc-w26
