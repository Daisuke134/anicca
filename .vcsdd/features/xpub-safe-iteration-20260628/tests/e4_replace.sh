#!/usr/bin/env bash
# E4 — verify replace_image_in_draft.py has --help AND its URL guard rejects
# non-draft URLs without touching the browser.
set -eu
SCRIPT=~/.claude/skills/x-article-publisher/scripts/replace_image_in_draft.py

# --help works
python3 "$SCRIPT" --help > /dev/null
echo "E4a PASS: --help exits 0"

# URL guard rejects bad URL with non-zero exit
# Pass an EXISTING src so a "src missing" error cannot mask a missing URL
# check (= adversary r2 finding: src.exists() ran BEFORE URL guard, so any
# nonexistent src trivially "passed" the test).
TMPSRC=$(mktemp -t e4src.XXXXXX.jpg)
printf '\xff\xd8\xff\xe0\x00\x10JFIF' > "$TMPSRC"
trap 'rm -f "$TMPSRC"' EXIT
OUTPUT=$(python3 "$SCRIPT" \
    --draft-url https://example.com/abc \
    --index 0 \
    --src "$TMPSRC" \
    --anchor "x" 2>&1 || true)
# Require the EXACT guard message — not any error that happens to contain
# "missing" or "draft". This proves the URL guard fired, not some other
# downstream failure.
if echo "$OUTPUT" | grep -qF "refusing to operate on non-draft URL" ; then
  echo "E4b PASS: URL guard rejected non-draft URL with the load-bearing message"
else
  echo "E4b FAIL: URL guard did not fire (script output below):"
  echo "$OUTPUT"
  exit 1
fi
