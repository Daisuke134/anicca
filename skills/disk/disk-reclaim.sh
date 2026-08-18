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

  # --- gig releases no plist points at --------------------------------------
  # On 2026-08-18 ~/gig/releases held 95 life-manager builds while the live
  # plists referenced 6. The disk filled, apply died with ENOSPC and reported
  # effect 0, which read as a quality problem until the log was opened. Five
  # janitors had been running and none of them could see this pile.
  #
  # Same rule as the clones above: referenced, not old. A release is a plain
  # `git archive` export of a sha, so an unreferenced one costs seconds to
  # rebuild - but deleting a referenced one takes a money lane down.
  releases_freed=$(python3 - <<'PY'
import pathlib, plistlib, re, shutil, subprocess, os, time

SHA = re.compile(r"^[0-9a-f]{40}$")
# A builder cuts releases every few minutes and repoints the plist afterwards, so a young
# unreferenced release is usually one that is mid-promotion rather than one nobody wants.
MIN_AGE_SECONDS = 7200

home = pathlib.Path.home()
keep = set()
for p in (home / "Library/LaunchAgents").glob("*.plist"):
    try:
        payload = plistlib.loads(p.read_bytes())
    except Exception:
        continue
    keep |= set(re.findall(r"releases/[a-z-]+/([0-9a-f]{40})", str(payload)))
ps = subprocess.run(["ps", "-axww", "-o", "command"], capture_output=True, text=True).stdout
keep |= set(re.findall(r"releases/[a-z-]+/([0-9a-f]{40})", ps))

# `current` and `previous` are how a lane rolls forward and back. Their targets are claimed even
# when no plist spells the sha out.
for lane in (home / "gig/releases").glob("*"):
    if not lane.is_dir():
        continue
    for link in lane.iterdir():
        if link.is_symlink():
            keep |= set(re.findall(r"([0-9a-f]{40})", os.path.realpath(link)))

# Refuse to run blind: if nothing claims a release, the readback failed rather
# than every lane being idle, and deleting on that reading wipes production.
freed = 0
if keep:
    for lane in (home / "gig/releases").glob("*"):
        if not lane.is_dir():
            continue
        for release in lane.iterdir():
            # `current` is a symlink to the live release; only sha-named real directories qualify.
            if release.is_symlink() or not release.is_dir() or not SHA.match(release.name):
                continue
            if release.name in keep or time.time() - release.stat().st_mtime < MIN_AGE_SECONDS:
                continue
            size = sum(f.stat().st_size for f in release.rglob("*") if f.is_file())
            for root, dirs, files in os.walk(release):
                os.chmod(root, 0o755)
                for name in files:
                    try:
                        os.chmod(os.path.join(root, name), 0o644)
                    except OSError:
                        pass
            shutil.rmtree(release, ignore_errors=True)
            if not release.exists():
                freed += size
print(freed // 1048576)
PY
)
  freed_mb=$((freed_mb + ${releases_freed:-0}))
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
