#!/usr/bin/env bash
# publish-devto.sh — wrap article-writer/post-devto.py for ai-entity-article-writer
# Usage:
#   bash publish-devto.sh --markdown-file <f> --title <t> --meta <m>

set -euo pipefail

MD_FILE=""
TITLE=""
META=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --markdown-file) MD_FILE="$2"; shift 2 ;;
    --title)         TITLE="$2"; shift 2 ;;
    --meta)          META="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done
[[ -f "$MD_FILE" ]] || { echo "FATAL: markdown not found: $MD_FILE" >&2; exit 1; }

if ! grep -q '^title:' "$MD_FILE"; then
  echo "FATAL: markdown missing 'title:' frontmatter" >&2; exit 1
fi
if ! grep -q '^tags:' "$MD_FILE"; then
  echo "FATAL: markdown missing 'tags:' frontmatter (dev.to requires tags)" >&2; exit 1
fi

# Managed exact8 runs use the tracked, ID-preserving Dev.to driver. It stages
# published:false, records the authenticated numeric article ID, and later
# flips only that ID live. The legacy workspace adapter below remains for
# unmanaged/manual draft calls.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- fail-closed PII gate (scripts/pii-gate.py) ---------------------------------------
# Nothing operator-identifying may reach Dev.to. ANY non-zero exit from the gate -- a finding,
# an unconfigured blocklist, or an internal scanner error -- aborts this publish. Gate output
# goes to stderr so it cannot pollute this script's single-line stdout contract.
python3 "$SCRIPT_DIR/pii-gate.py" --stage publish-devto "$MD_FILE" >&2 || exit $?

if [[ -n "${ARTICLE_RUN_DIR:-}" || -n "${ARTICLE_PUBLICATION_STATE:-}" || -n "${ARTICLE_LEDGER:-}" ]]; then
  set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a
  STAGED="$(python3 "$SCRIPT_DIR/devto-publish/devto.py" stage)" || exit $?
  ARTICLE_ID="$(printf '%s' "$STAGED" | jq -r '.article_id // empty')"
  DASHBOARD_URL="$(printf '%s' "$STAGED" | jq -r '.dashboard_url // empty')"
  [[ "$ARTICLE_ID" =~ ^[0-9]+$ && -n "$DASHBOARD_URL" ]] || {
    echo "FATAL: managed Dev.to stage returned malformed evidence: $STAGED" >&2
    exit 4
  }
  echo "DRAFT id=$ARTICLE_ID url=$DASHBOARD_URL"
  exit 0
fi

# Copy to article-writer drafts/<today>/en.md
# post-devto.py defaults ARTICLE_DATE to date.today() (local/JST) when unset, so this
# MUST use local date too -- using UTC here (as before) creates a ~9h window every day
# where this script writes to yesterday's UTC-dated dir while post-devto.py looks for
# today's JST-dated dir, and publish fails with "draft not found" (hit 2026-07-13).
TODAY="$(date +%Y-%m-%d)"
DRAFT_DIR="$HOME/.openclaw/workspace/article-writer/drafts/$TODAY"
mkdir -p "$DRAFT_DIR"
cp "$MD_FILE" "$DRAFT_DIR/en.md"

set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a
[[ -n "${DEVTO_API_KEY:-}" ]] || { echo "FATAL: DEVTO_API_KEY missing" >&2; exit 2; }

OUT="$(ARTICLE_DATE="$TODAY" python3 "$HOME/.openclaw/skills/article-writer/scripts/post-devto.py" 2>&1)"
EC=$?
if [[ $EC -ne 0 ]]; then
  echo "FATAL: post-devto.py failed (exit=$EC):" >&2
  printf '%s\n' "$OUT" >&2
  exit $EC
fi

URL="$(printf '%s\n' "$OUT" | grep -oE 'https://dev\.to/[^/[:space:]]+/[^[:space:]]+' | head -1)"
if [[ -z "$URL" ]]; then
  echo "FATAL: post-devto.py succeeded but URL not found" >&2
  printf '%s\n' "$OUT" >&2
  exit 4
fi
echo "$URL"
