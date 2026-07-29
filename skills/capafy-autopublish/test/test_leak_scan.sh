#!/usr/bin/env bash
set -uo pipefail
S="$(cd "$(dirname "$0")/.." && pwd)/scripts/leak_scan.sh"
tmp=$(mktemp -d); mkdir -p "$tmp/.claude/skills/x"
echo "# clean skill" > "$tmp/.claude/skills/x/SKILL.md"
bash "$S" "$tmp" >/dev/null 2>&1; c1=$?
echo 'key=AIzaSyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' > "$tmp/.claude/skills/x/leak.txt"
bash "$S" "$tmp" >/dev/null 2>&1; c2=$?
rm "$tmp/.claude/skills/x/leak.txt"; echo "secret" > "$tmp/.claude/skills/x/.env"
bash "$S" "$tmp" >/dev/null 2>&1; c3=$?
rm -rf "$tmp"
[ "$c1" = 0 ] && [ "$c2" = 1 ] && [ "$c3" = 1 ] && echo "PASS" || { echo "FAIL c1=$c1 c2=$c2 c3=$c3"; exit 1; }
