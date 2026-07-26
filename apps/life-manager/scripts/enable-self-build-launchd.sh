#!/usr/bin/env bash
# Re-enable the daily DEV self-build schedule (spec §10 row 10f).
#
# THIS SCRIPT IS SHIPPED, NOT RUN, BY THE ATOMIC THAT ADDED IT. Loading a launchd job is a real,
# recurring side effect on Dais's machine; it happens once, deliberately, after the PR is merged.
# Nothing in the loop calls this file — the loop must never be able to schedule itself.
#
# What it does, in order:
#   1. refuses unless the merge guard and the self-build entrypoint are both present on main;
#   2. removes the pause marker left by the "paused until final phase" decision;
#   3. writes the ACTIVE plist from the parked ai.anicca.life-manager-dev.plist.disabled, repointed
#      at skills/life-manager/self-build-daily.sh and pinned to 04:10;
#   4. bootstraps the job and reads back what launchd actually thinks, rather than assuming.
#
# TIME ZONE. launchd StartCalendarInterval is LOCAL time with no time-zone field (Apple, "Creating
# Launch Daemons and Agents"). This machine runs Asia/Tokyo, so Hour=4 Minute=10 IS 04:10 JST. The
# script asserts the machine's zone rather than trusting it: on a machine set to anything else, 4:10
# local would silently not be 4:10 JST and the "distinct real day" boundary would drift.
#
# Usage:  apps/life-manager/scripts/enable-self-build-launchd.sh          # enable + read back
#         apps/life-manager/scripts/enable-self-build-launchd.sh --status # read back only
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

LABEL="ai.anicca.life-manager-dev"
AGENTS="$HOME/Library/LaunchAgents"
PARKED="$AGENTS/$LABEL.plist.disabled"
ACTIVE="$AGENTS/$LABEL.plist"
PAUSE_MARKER="$HOME/.openclaw/state/life-manager-dev/PAUSED_UNTIL_FINAL_PHASE"
DOMAIN="gui/$(id -u)"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${LM_SELFBUILD_REPO:-$(cd "$HERE/../../.." && pwd)}"
ENTRYPOINT="$REPO_ROOT/skills/life-manager/self-build-daily.sh"
NODE_BIN="${NODE_BIN:-$(command -v node || echo /opt/homebrew/bin/node)}"

status() {
  printf '--- launchd readback ---\n'
  launchctl print "$DOMAIN/$LABEL" 2>/dev/null \
    | grep -E 'state|last exit|runs =|program|Hour|Minute' || printf 'label not loaded\n'
  printf '--- ledger ---\n'
  "$NODE_BIN" "$REPO_ROOT/apps/life-manager/scripts/self-build-daily.js" --status || true
}

if [ "${1:-}" = "--status" ]; then
  status
  exit 0
fi

[ -f "$PARKED" ] || { printf 'parked plist missing: %s\n' "$PARKED" >&2; exit 1; }
[ -x "$ENTRYPOINT" ] || { printf 'entrypoint missing or not executable: %s\n' "$ENTRYPOINT" >&2; exit 1; }
[ -f "$REPO_ROOT/apps/life-manager/lib/dev-merge-guard.js" ] \
  || { printf 'merge guard missing; 10e must be merged first\n' >&2; exit 1; }

# A reviewer that cannot be spawned fails CLOSED, so nothing unsafe merges — but the loop would
# then run seven days and merge nothing, and nobody would know why until day seven. Resolve it now,
# under the PATH the job will actually get, and refuse to enable a loop whose judge is missing.
JOB_PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
REVIEW_CLI_RESOLVED="$(PATH="$JOB_PATH" "$NODE_BIN" -e '
    const { resolveReviewCli } = require(process.argv[1]);
    process.stdout.write(resolveReviewCli(process.env));
  ' "$HERE/dev-adversary-review.js")"
if [ "$REVIEW_CLI_RESOLVED" = "claude" ]; then
  printf 'the fresh-reviewer CLI does not resolve under the job PATH; refusing to enable\n' >&2
  exit 1
fi
printf 'reviewer resolves to: %s\n' "$REVIEW_CLI_RESOLVED"

ZONE="$(readlink /etc/localtime | sed 's#.*/zoneinfo/##')"
if [ "$ZONE" != "Asia/Tokyo" ]; then
  printf 'machine time zone is %s, not Asia/Tokyo — 04:10 local would not be 04:10 JST\n' "$ZONE" >&2
  exit 1
fi

# The plist is written fresh rather than sed-patched: the parked copy still points at the OLD
# PR-producing runner (scripts/life-manager-dev-daily.js), and a half-patched plist is worse than a
# regenerated one. The parked file stays on disk as the historical record.
cp "$PARKED" "$PARKED.pre-10f.$(date +%s)"
cat > "$ACTIVE" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$ENTRYPOINT</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key>
    <string>$HOME</string>
    <!-- \$HOME/.local/bin is NOT decoration: measured 2026-07-27, the reviewer CLI (\`claude\`) lives
         there and nowhere else on this machine. The parked plist omitted it, which would have made
         every review fail closed and the loop merge nothing for seven days. -->
    <key>PATH</key>
    <string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>LM_SELFBUILD_REPO</key>
    <string>$REPO_ROOT</string>
  </dict>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>4</integer>
    <key>Minute</key>
    <integer>10</integer>
  </dict>
  <key>RunAtLoad</key>
  <false/>
  <key>StandardOutPath</key>
  <string>$HOME/.openclaw/logs/life-manager-dev.out.log</string>
  <key>StandardErrorPath</key>
  <string>$HOME/.openclaw/logs/life-manager-dev.err.log</string>
</dict>
</plist>
PLIST
chmod 600 "$ACTIVE"
plutil -lint "$ACTIVE"

rm -f "$PAUSE_MARKER"

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$ACTIVE"
launchctl enable "$DOMAIN/$LABEL"

status
printf '\nenabled. 04:10 Asia/Tokyo daily. Merely loading the plist is NOT evidence:\n'
printf 'the day is proven when a new row appears in the self-build ledger.\n'
