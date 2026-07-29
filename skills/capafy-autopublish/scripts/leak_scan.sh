#!/usr/bin/env bash
# usage: leak_scan.sh <staging_dir>  — 秘密/denylist検出で exit 1 (fail-closed)
set -uo pipefail
DIR="${1:?staging dir required}"
fail=0
while IFS= read -r f; do
  echo "DENYLIST FILE: $f"; fail=1
done < <(find "$DIR" -type f \( -name 'CLAUDE.md' -o -name '.env*' -o -name 'settings*.json' -o -name '.credentials*' -o -name '*token*' -o -name '*secret*' \) 2>/dev/null | grep -v '_scan_only')
if grep -rolE 'AIzaSy[A-Za-z0-9_-]{20,}|sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{20,}|am_sk_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|xox[bap]-[A-Za-z0-9-]{10,}|rf_[A-Za-z0-9_]{24,}' "$DIR" 2>/dev/null | grep -v 'PLATFORM_MANAGED' | grep -q .; then
  echo "SECRET PATTERN DETECTED"; fail=1
fi
if [ "$fail" -eq 0 ]; then echo "LEAK_SCAN: clean"; exit 0; else echo "LEAK_SCAN: FAIL (fail-closed)"; exit 1; fi
