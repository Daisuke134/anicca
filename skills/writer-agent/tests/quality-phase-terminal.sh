#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
HELPER="$ROOT/skills/article-writer/scripts/quality-phase-terminal.py"
TMP="$(mktemp -d /tmp/article-quality-terminal.XXXXXX)"
trap 'rm -rf -- "$TMP"' EXIT
RUN="$TMP/run"
MD="$TMP/article.md"
mkdir -p "$RUN/gates"
printf '# Stable article\n' >"$MD"

# Missing quality evidence never becomes a terminal publish artifact.
if python3 "$HELPER" write --run-dir "$RUN" --lang ja --markdown-file "$MD"; then
  echo 'FAIL: missing editorial/reader receipts became terminal' >&2
  exit 1
fi

HASH="$(shasum -a 256 "$MD" | awk '{print $1}')"
printf '%s\n' "{\"verdict\":\"PASS\",\"article_sha256\":\"$HASH\"}" >"$RUN/gates/editorial-en.json"
printf '%s\n' "{\"status\":\"pass\",\"article_sha256\":\"$HASH\",\"payload\":{\"verdict\":\"PASS\"}}" >"$RUN/gates/reader-testing-gate-en.terminal.json"
printf '%s\n' "{\"verdict\":\"PASS\",\"article_sha256\":\"$HASH\",\"violations\":[]}" >"$RUN/gates/identity-en.json"

# Editorial + reader + safety terminal markers are hash-bound.
python3 "$HELPER" write --run-dir "$RUN" --lang en --markdown-file "$MD"
python3 "$HELPER" check --run-dir "$RUN" --lang en --markdown-file "$MD"
printf '\nChanged.\n' >>"$MD"
if python3 "$HELPER" check --run-dir "$RUN" --lang en --markdown-file "$MD"; then
  echo 'FAIL: stale quality marker accepted a changed article' >&2
  exit 1
fi

rg -q 'quality-phase-terminal\.py.*check' "$ROOT/skills/article-writer/scripts/run.sh"
rg -q 'quality-phase-terminal\.py.*check' "$ROOT/skills/article-writer/scripts/x-publish/publish-to-x.sh"
rg -q 'quality-phase-terminal\.py.*write' "$ROOT/skills/article-writer/scripts/conscience-gate.sh"

echo 'PASS: terminal quality evidence skips channel reruns and new markers are hash-bound'
