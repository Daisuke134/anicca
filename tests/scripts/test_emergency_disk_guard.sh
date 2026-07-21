#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
GUARD="$ROOT/scripts/emergency-disk-guard.sh"
TMP=$(mktemp -d /tmp/emergency-guard-test.XXXXXX)
trap 'rm -rf "$TMP"' EXIT

HOME_DIR="$TMP/home"
STATE_DIR="$HOME_DIR/.openclaw/state"
LEASE_DIR="$STATE_DIR/gig-workers"
CANONICAL_ARGV="/bin/bash $HOME_DIR/profitable-claude/skills/gig-work/gig_pass.sh"
mkdir -p "$HOME_DIR/.claude/projects/incident" "$HOME_DIR/gig" "$LEASE_DIR"
mkdir -p "$HOME_DIR/.cloak/profiles/inactive/Default/Cache" "$HOME_DIR/.cloak/profiles/inactive/Default/Code Cache" "$HOME_DIR/.cloak/profiles/inactive/Default/GPUCache"
mkdir -p "$HOME_DIR/Library/Application Support/Claude/vm_bundles/active.bundle"
mkdir -p "$HOME_DIR/Library/Application Support/Claude/vm_bundles/error.bundle"
mkdir -p "$HOME_DIR/.cache/codex-runtimes" "$HOME_DIR/.cache/whisper" "$HOME_DIR/.cache/torch"
mkdir -p "$HOME_DIR/.codex/.tmp" "$HOME_DIR/.openclaw/workspace/runs/run-1"
LEGACY_RECLAIMS="$STATE_DIR/emergency-disk-guard-reclaim.tsv"
cat > "$LEGACY_RECLAIMS" <<'EOF'
2026-07-20T00:00:00Z	/legacy/cache	legacy	ephemeral-cache	4096	old-format	p0-containment-v1	removed
2026-07-20T00:01:00Z	/legacy/cache2	legacy	ephemeral-cache	0	old-format	p0-containment-v1	failed
EOF
LEGACY_HASH_BEFORE=$(shasum -a 256 "$LEGACY_RECLAIMS" | awk '{print $1}')
printf 'active evidence\n' > "$HOME_DIR/.claude/projects/incident/active.jsonl"
printf '4242\n' > "$HOME_DIR/gig/.pass.lock"
printf 'cookie identity\n' > "$HOME_DIR/.cloak/profiles/inactive/Default/Cookies"
printf 'login identity\n' > "$HOME_DIR/.cloak/profiles/inactive/Default/Login Data"
printf 'cache\n' > "$HOME_DIR/.cloak/profiles/inactive/Default/Cache/data"
printf 'code cache\n' > "$HOME_DIR/.cloak/profiles/inactive/Default/Code Cache/data"
printf 'gpu cache\n' > "$HOME_DIR/.cloak/profiles/inactive/Default/GPUCache/data"
printf 'active vm state\n' > "$HOME_DIR/Library/Application Support/Claude/vm_bundles/active.bundle/sessiondata.img"
printf 'must survive lsof error\n' > "$HOME_DIR/Library/Application Support/Claude/vm_bundles/error.bundle/sessiondata.img"
printf 'runtime cache\n' > "$HOME_DIR/.cache/codex-runtimes/runtime"
printf 'remove must fail closed\n' > "$HOME_DIR/.cache/torch/model"
printf 'plugin staging\n' > "$HOME_DIR/.codex/.tmp/staged-plugin"
printf 'deliverable intermediate\n' > "$HOME_DIR/.openclaw/workspace/runs/run-1/reel-text.mp4"
printf 'unknown class payload\n' > "$TMP/unknown-class"
touch -t 202001010000 "$HOME_DIR/.claude/projects/incident/active.jsonl" "$HOME_DIR/gig/.pass.lock" "$HOME_DIR/.openclaw/workspace/runs/run-1/reel-text.mp4"

write_lease() {
  local pid=$1 start=$2 pgid=$3 argv=$4
  cat > "$LEASE_DIR/$pid.lease" <<EOF
pid=$pid
start_token=$start
pgid=$pgid
canonical_argv=$argv
EOF
}

write_lease 1101 start-1101 1101 "$CANONICAL_ARGV"
write_lease 1103 start-1103 1103 "$CANONICAL_ARGV"
write_lease 1106 expected-start 1106 "$CANONICAL_ARGV"
write_lease 1107 start-1107 1107 "$CANONICAL_ARGV"
write_lease 1108 start-1108 2200 "$CANONICAL_ARGV"
write_lease 1109 start-1109 1109 "$CANONICAL_ARGV"
write_lease 1110 start-1110 1110 "$CANONICAL_ARGV"
write_lease 1111 start-1111 1111 "$CANONICAL_ARGV"

# pid, initial start token, initial pgid, elapsed, initial argv,
# recheck start token, recheck pgid, recheck argv, post-stop group state.
cat > "$TMP/processes.tsv" <<EOF
1101	start-1101	1101	10	$CANONICAL_ARGV	start-1101	1101	$CANONICAL_ARGV	alive
1103	start-1103	1103	99999	$CANONICAL_ARGV	start-1103	1103	$CANONICAL_ARGV	gone
1104	start-1104	1104	99999	claude --name anicca-gig-core Coconala gig	start-1104	1104	claude --name anicca-gig-core Coconala gig	alive
1105	start-1105	1105	99999	tmux new-session /bin/bash $HOME_DIR/profitable-claude/skills/gig-work/gig_pass.sh	start-1105	1105	tmux new-session /bin/bash $HOME_DIR/profitable-claude/skills/gig-work/gig_pass.sh	alive
1106	reused-start	1106	99999	$CANONICAL_ARGV	reused-start	1106	$CANONICAL_ARGV	alive
1107	start-1107	1107	99999	/bin/bash /tmp/gig_pass.sh --name anicca-gig-core	start-1107	1107	/bin/bash /tmp/gig_pass.sh --name anicca-gig-core	alive
1108	start-1108	2200	99999	$CANONICAL_ARGV	start-1108	2200	$CANONICAL_ARGV	alive
1109	start-1109	1109	99999	$CANONICAL_ARGV	changed-before-signal	1109	$CANONICAL_ARGV	alive
1110	start-1110	1110	not-a-number	$CANONICAL_ARGV	start-1110	1110	$CANONICAL_ARGV	alive
1111	start-1111	1111	99999	$CANONICAL_ARGV	start-1111	1111	$CANONICAL_ARGV	survivor
EOF

EMERGENCY_GUARD_TEST_HOME="$HOME_DIR" \
EMERGENCY_GUARD_TEST_FREE_GB=2 \
EMERGENCY_GUARD_TEST_NOW_EPOCH=100000 \
EMERGENCY_GUARD_TEST_PROCESS_FIXTURE="$TMP/processes.tsv" \
EMERGENCY_GUARD_TEST_ENABLE_RECLAIM=1 \
EMERGENCY_GUARD_TEST_ACTIVE_PROFILE="$HOME_DIR/.cloak/profiles/inactive" \
EMERGENCY_GUARD_TEST_OPEN_PATH="$HOME_DIR/Library/Application Support/Claude/vm_bundles/active.bundle" \
EMERGENCY_GUARD_TEST_LSOF_ERROR_PATH="$HOME_DIR/Library/Application Support/Claude/vm_bundles/error.bundle" \
EMERGENCY_GUARD_TEST_LOCK_OWNER=1101 \
EMERGENCY_GUARD_TEST_HEARTBEAT_PID=1101 \
EMERGENCY_GUARD_TEST_KILL_LEDGER="$TMP/killed.tsv" \
EMERGENCY_GUARD_TEST_EXTRA_RECLAIM="$TMP/unknown-class" \
EMERGENCY_GUARD_TEST_RM_FAIL_PATH="$HOME_DIR/.cache/torch" \
GIG_WORKER_CANONICAL_ARGV="$CANONICAL_ARGV" \
bash "$GUARD" || guard_rc=$?
test "${guard_rc:-0}" -eq 3 || { echo "low reserve with incomplete recovery returned rc=${guard_rc:-0}"; exit 1; }

DECISIONS="$STATE_DIR/emergency-disk-guard-decisions.tsv"
RECLAIMS="$STATE_DIR/emergency-disk-guard-reclaim-v2.tsv"

test -e "$HOME_DIR/.claude/projects/incident/active.jsonl" || { echo 'active transcript was deleted'; exit 1; }
test -e "$HOME_DIR/gig/.pass.lock" || { echo 'active lock was deleted'; exit 1; }
test ! -e "$HOME_DIR/.cloak/profiles/inactive/Default/Cache" || { echo 'regenerable cache was not reclaimed'; exit 1; }
test -e "$HOME_DIR/.cloak/profiles/inactive/Default/Cookies" || { echo 'browser cookie identity was deleted'; exit 1; }
test -e "$HOME_DIR/.cloak/profiles/inactive/Default/Login Data" || { echo 'browser login identity was deleted'; exit 1; }
test -e "$HOME_DIR/Library/Application Support/Claude/vm_bundles/active.bundle/sessiondata.img" || { echo 'active VM state was unlinked'; exit 1; }
test -e "$HOME_DIR/Library/Application Support/Claude/vm_bundles/error.bundle/sessiondata.img" || { echo 'lsof error was treated as confirmed closed'; exit 1; }
test -e "$HOME_DIR/.openclaw/workspace/runs/run-1/reel-text.mp4" || { echo 'unfinalized reel-text.mp4 was deleted by mtime'; exit 1; }
test -e "$TMP/unknown-class" || { echo 'unknown reclaim class was deleted'; exit 1; }
test -d "$HOME_DIR/.cache/whisper" || { echo 'zero-byte path was deleted instead of failing closed'; exit 1; }
test -e "$HOME_DIR/.cache/torch/model" || { echo 'failed removal did not preserve the path'; exit 1; }
test "$(shasum -a 256 "$LEGACY_RECLAIMS" | awk '{print $1}')" = "$LEGACY_HASH_BEFORE" || {
  echo 'legacy 8-column reclaim ledger was modified'
  exit 1
}

test -e "$TMP/killed.tsv" || { echo 'missing signal ledger'; exit 1; }
test "$(cut -f1 "$TMP/killed.tsv" | sort | tr '\n' ' ')" = '1103 1111 ' || {
  echo 'only exact, leased, stale dedicated process groups may be signaled'
  cat "$TMP/killed.tsv"
  exit 1
}

grep -q $'^1101\tpreserve\tfresh-heartbeat$' "$DECISIONS"
grep -q $'^1103\tstopped\tstale-runaway$' "$DECISIONS"
grep -q $'^1106\tpreserve\tlease-start-token-mismatch$' "$DECISIONS"
grep -q $'^1107\tpreserve\tlease-argv-mismatch$' "$DECISIONS"
grep -q $'^1108\tpreserve\tlease-not-dedicated-pgid$' "$DECISIONS"
grep -q $'^1109\tpreserve\trevalidation-failed$' "$DECISIONS"
grep -q $'^1110\tpreserve\tinvalid-elapsed$' "$DECISIONS"
grep -q $'^1111\tfailed\tprocess-group-survived$' "$DECISIONS"
! grep -q $'^1104\t' "$DECISIONS" || { echo 'core was discovered without a lease'; exit 1; }
! grep -q $'^1105\t' "$DECISIONS" || { echo 'substring match was treated as a worker'; exit 1; }

# Every attempted reclaim has planned + exactly one terminal row. Unknown class
# and zero-byte paths fail closed; successful rows carry positive reclaimed bytes.
test "$(head -1 "$RECLAIMS")" = $'timestamp\ttxid\tphase\tpath\towner\tclass\tbefore_bytes\tafter_bytes\treclaimed_bytes\treason\tpolicy_version\tdetail'
awk -F '\t' 'NF != 12 { exit 1 }' "$RECLAIMS"
tail -n +2 "$RECLAIMS" | awk -F '\t' '
  $3 == "planned" { planned[$2]++ }
  $3 == "removed" || $3 == "failed" { terminal[$2]++ }
  END {
    for (tx in planned) if (planned[tx] != 1 || terminal[tx] != 1) exit 1
    for (tx in terminal) if (planned[tx] != 1 || terminal[tx] != 1) exit 1
  }
'
grep -q $'\tfailed\t.*\tunknown-class\t' "$RECLAIMS"
grep -q $'\tfailed\t.*\.cache/whisper\t' "$RECLAIMS"
grep -q $'\tfailed\t.*\.cache/torch\t.*\tremove-command-failed$' "$RECLAIMS"
awk -F '\t' '$3 == "removed" && ($9 !~ /^[0-9]+$/ || $9 <= 0) { exit 1 }' "$RECLAIMS"
grep -q 'lsof-error-preserved' "$DECISIONS"

echo 'PASS: fail-closed reclaim and lease-bound process-group containment'
