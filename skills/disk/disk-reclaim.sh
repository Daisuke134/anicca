#!/usr/bin/env bash
# Reclaim disk without touching anything that carries state.
#
# Written after free space hit 2GB on 2026-08-18 and nearly stopped the work.
# The cause was not big files - it was processes that never close. macOS makes a
# code-sign clone every time a browser launches, and 27 of them (9.5GB) had been
# left behind by browsers that did not exit cleanly.
#
# THE RULE THAT MATTERS: a clone is orphaned only when no process holds a handle
# on it. Never decide by age or count - the CloakBrowser instances stay up for
# days, so "old" does not mean "unused".
set -uo pipefail

STATE="${HOME}/.local/state/disk-reclaim"
LOG="${STATE}/reclaim.jsonl"
LOW_WATER_GB=15      # start reclaiming below this
ALERT_GB=8           # shout below this
mkdir -p "$STATE"

avail_gb() { df -g /System/Volumes/Data | tail -1 | awk '{print $4}'; }

BEFORE=$(avail_gb)
freed_mb=0
removed=0

if [ "$BEFORE" -lt "$LOW_WATER_GB" ]; then
  # --- orphaned code-sign clones -------------------------------------------
  INUSE="$(mktemp)"
  sudo lsof 2>/dev/null | grep -o "code_sign_clone\.[A-Za-z0-9]*" | sort -u > "$INUSE"
  while read -r dir; do
    name=$(basename "$dir")
    grep -qx "$name" "$INUSE" && continue          # a live process holds it
    size=$(sudo du -sm "$dir" 2>/dev/null | cut -f1)
    sudo rm -rf "$dir" 2>/dev/null
    [ -d "$dir" ] || { removed=$((removed + 1)); freed_mb=$((freed_mb + ${size:-0})); }
  done < <(sudo find /private/var/folders -maxdepth 3 -name "code_sign_clone.*" -type d 2>/dev/null)
  rm -f "$INUSE"

  # --- leases whose holder is gone -----------------------------------------
  for f in "$HOME"/.cloak/leases/*.lease; do
    [ -f "$f" ] || continue
    pid=$(python3 -c "import json;print(json.load(open('$f'))['pid'])" 2>/dev/null) || continue
    ident=$(python3 -c "import json;print(json.load(open('$f'))['identity'])" 2>/dev/null) || continue
    ps -p "$pid" >/dev/null 2>&1 && continue
    "$HOME/.config/ai/bin/browser-guard.sh" release "$ident" >/dev/null 2>&1
  done
fi

AFTER=$(avail_gb)
printf '{"at":"%s","before_gb":%s,"after_gb":%s,"clones_removed":%s,"freed_mb":%s}\n' \
  "$(date -u +%FT%TZ)" "$BEFORE" "$AFTER" "$removed" "$freed_mb" >> "$LOG"
echo "free ${BEFORE}G -> ${AFTER}G, removed ${removed} clones (${freed_mb}MB)"

if [ "$AFTER" -lt "$ALERT_GB" ]; then
  set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
    curl -s -o /dev/null -X POST \
      "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d chat_id=8547730585 \
      --data-urlencode "text=Claude::: ディスク残り ${AFTER}GB。自動回収後もこの値です。長時間起動しっぱなしのアプリとスワップ(/System/Volumes/VM)を確認してください。"
  fi
fi
