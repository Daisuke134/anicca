#!/usr/bin/env bash
# openclaw-core-backup.sh — keep the parts of ~/.openclaw that cannot be rebuilt.
#
# `openclaw backup create` exists but is not usable here as a scheduled job: it
# defaults to the CURRENT directory (2026-07-27 it wrote a 12.8GB credentials archive
# into a git repo root, unignored), and even with --no-include-workspace it produced
# 11GB against 3.9Gi of free space -- ENOSPC on the next run. Measured, the whole of
# ~/.openclaw is 15G, but everything irreplaceable is 55M:
#
#   credentials/     4K    channel + pairing secrets
#   openclaw.json   28K    config AND auth.profiles (oauth/token identities)
#   cron/jobs.json  9.0M   316 scheduled jobs
#   identity/       56M    device identity
#   devices/        8.0K
#
# Sessions, agents and logs are the other 15G. Losing them costs history, not the
# ability to come back up, so they are deliberately out of scope.
set -uo pipefail

DEST="${OPENCLAW_BACKUP_DIR:-$HOME/.openclaw-backups}"
KEEP="${OPENCLAW_BACKUP_KEEP:-2}"
MIN_FREE_MB="${OPENCLAW_BACKUP_MIN_FREE_MB:-2048}"
STAMP=$(date +%Y%m%d-%H%M%S)
ARCHIVE="$DEST/openclaw-core-$STAMP.tar.gz"

mkdir -p "$DEST" || exit 1

# Refuse to run the disk to zero. A backup that starves the loops it exists to
# protect is not a backup.
FREE_MB=$(df -m "$DEST" | awk 'NR==2 {print $4}')
if [ "${FREE_MB:-0}" -lt "$MIN_FREE_MB" ]; then
  echo "{\"status\":\"skipped\",\"reason\":\"low_disk\",\"free_mb\":${FREE_MB:-0}}"
  exit 0
fi

cd "$HOME" || exit 1
TARGETS=()
for path in .openclaw/openclaw.json .openclaw/credentials .openclaw/cron/jobs.json \
            .openclaw/identity .openclaw/devices; do
  [ -e "$path" ] && TARGETS+=("$path")
done
if [ "${#TARGETS[@]}" -eq 0 ]; then
  echo '{"status":"failed","reason":"no_targets"}'
  exit 1
fi

umask 077   # the archive carries credentials; never group/world readable
if ! tar czf "$ARCHIVE" "${TARGETS[@]}" 2>/dev/null; then
  rm -f "$ARCHIVE"
  echo '{"status":"failed","reason":"tar_failed"}'
  exit 1
fi

# Read it back. An archive that was never opened is a claim, not a backup.
if ! tar tzf "$ARCHIVE" >/dev/null 2>&1; then
  rm -f "$ARCHIVE"
  echo '{"status":"failed","reason":"verify_failed"}'
  exit 1
fi

# Prune oldest beyond KEEP generations.
ls -1t "$DEST"/openclaw-core-*.tar.gz 2>/dev/null | tail -n +"$((KEEP + 1))" | while read -r old; do
  rm -f "$old"
done

SIZE=$(stat -f %z "$ARCHIVE")
COUNT=$(ls -1 "$DEST"/openclaw-core-*.tar.gz 2>/dev/null | wc -l | tr -d ' ')
echo "{\"status\":\"ok\",\"archive\":\"$ARCHIVE\",\"bytes\":$SIZE,\"generations\":$COUNT}"
