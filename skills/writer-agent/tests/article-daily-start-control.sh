#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
WRAPPER="$ROOT/skills/writer-agent/article-daily.sh"

grep -F 'article_daily_start_control.py' "$WRAPPER" >/dev/null
grep -F 'skip-complete' "$WRAPPER" >/dev/null
grep -F 'skip-pending-worker' "$WRAPPER" >/dev/null
! grep -F 'RESUME_EXISTING=' "$WRAPPER" >/dev/null

echo 'PASS: wrapper creates only a new daily run and leaves saved work to durable workers'
