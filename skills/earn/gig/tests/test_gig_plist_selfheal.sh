#!/usr/bin/env bash
# V3 failure-injection: reproduce the A17 incident (auditor plist overwritten with the
# 13-byte JSON fragment {"Minute":45}, 2026-07-30 21:54) in a sandbox dir and assert
# plist-selfheal.sh detects the corruption and restores the repo copy.
# File-reconcile layer only (GIG_PLIST_SKIP_LAUNCHCTL=1); the launchctl bootstrap path
# is exercised by the live 5-min gig-core-healthcheck run.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

AGENTS="$TMP/LaunchAgents"; LOGF="$TMP/selfheal.log"; REGISTRY="$TMP/gig.json"
mkdir -p "$AGENTS"

cat > "$REGISTRY" <<'JSON'
{
  "agents": {
    "ai.anicca.hf-gig-auditor": {"desired_state": "enabled"},
    "ai.anicca.hf-gig-pass": {"desired_state": "disabled"}
  }
}
JSON

fail() { echo "FAIL: $*"; exit 1; }

# --- injection 1: exact incident payload over the auditor plist ---
printf '{"Minute":45}' > "$AGENTS/ai.anicca.hf-gig-auditor.plist"
[ "$(stat -f %z "$AGENTS/ai.anicca.hf-gig-auditor.plist")" = "13" ] || fail "injection setup wrong"

GIG_LAUNCH_AGENTS_DIR="$AGENTS" GIG_LAUNCHD_REPO_DIR="$HERE/launchd" \
GIG_LAUNCHD_REGISTRY="$REGISTRY" GIG_PLIST_LOG="$LOGF" GIG_PLIST_SKIP_LAUNCHCTL=1 \
bash "$HERE/plist-selfheal.sh" || fail "selfheal exited nonzero on restorable corruption"

plutil -lint -s "$AGENTS/ai.anicca.hf-gig-auditor.plist" >/dev/null 2>&1 \
  || fail "auditor plist not restored to valid plist"
cmp -s "$AGENTS/ai.anicca.hf-gig-auditor.plist" "$HERE/launchd/ai.anicca.hf-gig-auditor.plist" \
  || fail "restored plist differs from repo canonical copy"
grep -q "BROKEN ai.anicca.hf-gig-auditor.plist" "$LOGF" || fail "corruption not logged"

# --- injection 2: disabled legacy plist remains untouched and cannot be revived ---
printf '{"Minute":45}' > "$AGENTS/ai.anicca.hf-gig-pass.plist"
GIG_LAUNCH_AGENTS_DIR="$AGENTS" GIG_LAUNCHD_REPO_DIR="$HERE/launchd" \
GIG_LAUNCHD_REGISTRY="$REGISTRY" GIG_PLIST_LOG="$LOGF" GIG_PLIST_SKIP_LAUNCHCTL=1 \
bash "$HERE/plist-selfheal.sh" || fail "selfheal exited nonzero while skipping retired plist"
[ "$(cat "$AGENTS/ai.anicca.hf-gig-pass.plist")" = '{"Minute":45}' ] \
  || fail "retired plist was restored or modified"
grep -q "RETIRED ai.anicca.hf-gig-pass -> no restore/bootstrap" "$LOGF" \
  || fail "retired plist skip not logged"

# --- injection 3: broken plist with NO registry entry is retired, not restored or bootstrapped ---
# NB: a bare word like 'garbage' lints OK as an old-style ASCII plist — use the real incident payload
printf '{"Minute":45}' > "$AGENTS/ai.anicca.hf-gig-no-such-agent.plist"
GIG_LAUNCH_AGENTS_DIR="$AGENTS" GIG_LAUNCHD_REPO_DIR="$HERE/launchd" \
GIG_LAUNCHD_REGISTRY="$REGISTRY" GIG_PLIST_LOG="$LOGF" GIG_PLIST_SKIP_LAUNCHCTL=1 \
bash "$HERE/plist-selfheal.sh" || fail "selfheal exited nonzero while skipping absent label"
[ "$(cat "$AGENTS/ai.anicca.hf-gig-no-such-agent.plist")" = '{"Minute":45}' ] \
  || fail "absent label was restored or modified"
grep -q "RETIRED ai.anicca.hf-gig-no-such-agent -> no restore/bootstrap" "$LOGF" \
  || fail "absent label skip not logged"

# --- no-op: healthy dir → exit 0, no BROKEN lines added ---
rm "$AGENTS/ai.anicca.hf-gig-no-such-agent.plist"
BEFORE="$(grep -c BROKEN "$LOGF")"
GIG_LAUNCH_AGENTS_DIR="$AGENTS" GIG_LAUNCHD_REPO_DIR="$HERE/launchd" \
GIG_LAUNCHD_REGISTRY="$REGISTRY" GIG_PLIST_LOG="$LOGF" GIG_PLIST_SKIP_LAUNCHCTL=1 \
bash "$HERE/plist-selfheal.sh" || fail "selfheal nonzero on healthy dir"
[ "$(grep -c BROKEN "$LOGF")" = "$BEFORE" ] || fail "healthy dir produced BROKEN log lines"

echo "PASS: test_gig_plist_selfheal (enabled restored; retired and absent skipped; healthy no-op)"
