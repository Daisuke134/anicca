#!/usr/bin/env bash
# article-daily propose — thin wrapper around _shared/propose-and-rewrite.sh
# Usage: bash propose.sh --channel <zenn|devto|substack-ja|substack-en|aniccaai-blog>
set -euo pipefail
CHANNEL=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --channel) CHANNEL="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done
[[ -n "$CHANNEL" ]] || { echo "FATAL: --channel required" >&2; exit 1; }

case "$CHANNEL" in
  zenn)            PLATFORM="Zenn"; ACCOUNT="anicca-daisuke"; LANG="ja" ;;
  devto)           PLATFORM="Dev.to"; ACCOUNT="anicca_ai"; LANG="en" ;;
  substack-ja)     PLATFORM="Substack"; ACCOUNT="aniccaai.substack.com"; LANG="ja" ;;
  substack-en)     PLATFORM="Substack"; ACCOUNT="aniccaai.substack.com"; LANG="en" ;;
  aniccaai-blog)   PLATFORM="aniccaai-blog"; ACCOUNT="aniccaai.com"; LANG="ja" ;;
  *) echo "FATAL: unknown channel: $CHANNEL" >&2; exit 1 ;;
esac

exec bash "$HOME/.openclaw/skills/_shared/propose-and-rewrite.sh" \
  --channel "article-${CHANNEL}" \
  --platform "$PLATFORM" \
  --account "$ACCOUNT" \
  --lang "$LANG" \
  --candidates 5
