#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
GUARD="$ROOT/scripts/emergency-disk-guard.sh"
TMP=$(mktemp -d /tmp/emergency-guard-test.XXXXXX)
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/home/.claude/projects/incident" "$TMP/home/gig" "$TMP/home/.openclaw/state"
mkdir -p "$TMP/home/.cloak/profiles/inactive/Default/Cache" "$TMP/home/.cloak/profiles/inactive/Default/Code Cache"
printf 'active evidence\n' > "$TMP/home/.claude/projects/incident/active.jsonl"
printf '4242\n' > "$TMP/home/gig/.pass.lock"
printf 'cookie identity\n' > "$TMP/home/.cloak/profiles/inactive/Default/Cookies"
printf 'login identity\n' > "$TMP/home/.cloak/profiles/inactive/Default/Login Data"
printf 'cache\n' > "$TMP/home/.cloak/profiles/inactive/Default/Cache/data"
printf 'code cache\n' > "$TMP/home/.cloak/profiles/inactive/Default/Code Cache/data"
touch -t 202001010000 "$TMP/home/.claude/projects/incident/active.jsonl" "$TMP/home/gig/.pass.lock"

cat > "$TMP/processes.tsv" <<'EOF'
1101	10	bash /tmp/gig_pass.sh
1102	9001	bash /tmp/gig_pass.sh
1103	99999	bash /tmp/gig_pass.sh
1104	99999	claude --name anicca-gig-core Coconala gig
EOF

EMERGENCY_GUARD_TEST_HOME="$TMP/home" \
EMERGENCY_GUARD_TEST_FREE_GB=2 \
EMERGENCY_GUARD_TEST_NOW_EPOCH=100000 \
EMERGENCY_GUARD_TEST_PROCESS_FIXTURE="$TMP/processes.tsv" \
EMERGENCY_GUARD_TEST_ENABLE_RECLAIM=1 \
EMERGENCY_GUARD_TEST_LOCK_OWNER=1101 \
EMERGENCY_GUARD_TEST_HEARTBEAT_PID=1102 \
EMERGENCY_GUARD_TEST_KILL_LEDGER="$TMP/killed.tsv" \
bash "$GUARD"

test -e "$TMP/home/.claude/projects/incident/active.jsonl" || { echo 'active transcript was deleted'; exit 1; }
test -e "$TMP/home/gig/.pass.lock" || { echo 'active lock was deleted'; exit 1; }
test ! -e "$TMP/home/.cloak/profiles/inactive/Default/Cache" || { echo 'regenerable cache was not reclaimed'; exit 1; }
test ! -e "$TMP/home/.cloak/profiles/inactive/Default/Code Cache" || { echo 'regenerable code cache was not reclaimed'; exit 1; }
test -e "$TMP/home/.cloak/profiles/inactive/Default/Cookies" || { echo 'browser cookie identity was deleted'; exit 1; }
test -e "$TMP/home/.cloak/profiles/inactive/Default/Login Data" || { echo 'browser login identity was deleted'; exit 1; }
test -e "$TMP/killed.tsv" || { echo 'missing kill ledger'; exit 1; }

test "$(cut -f1 "$TMP/killed.tsv" | sort | tr '\n' ' ')" = '1103 ' || {
  echo 'expected only stale runaway worker 1103 to be killed'
  cat "$TMP/killed.tsv"
  exit 1
}

grep -q $'^1101\tpreserve\tlock-owner$' "$TMP/home/.openclaw/state/emergency-disk-guard-decisions.tsv"
grep -q $'^1102\tpreserve\tfresh-heartbeat$' "$TMP/home/.openclaw/state/emergency-disk-guard-decisions.tsv"
grep -q $'^1103\tkill\tstale-runaway$' "$TMP/home/.openclaw/state/emergency-disk-guard-decisions.tsv"
grep -q $'^1104\tpreserve\tgig-core$' "$TMP/home/.openclaw/state/emergency-disk-guard-decisions.tsv"

echo 'PASS: core + normal worker + active evidence preserved; only stale runaway killed'
