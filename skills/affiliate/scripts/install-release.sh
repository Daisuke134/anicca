#!/usr/bin/env bash
set -euo pipefail

die() {
  printf 'affiliate release install: %s\n' "$*" >&2
  exit 1
}

SKILL_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
REPO_ROOT="$(cd -- "$SKILL_ROOT/../.." && pwd -P)"

command -v git >/dev/null 2>&1 || die "git is required"
[[ -f "$SKILL_ROOT/SKILL.md" ]] || die "canonical SKILL.md is missing"
[[ "$(git -C "$REPO_ROOT" rev-parse --is-inside-work-tree 2>/dev/null || true)" == "true" ]] \
  || die "canonical source must be inside a git worktree"
[[ "$(git -C "$REPO_ROOT" rev-parse --show-toplevel)" == "$REPO_ROOT" ]] \
  || die "git worktree root does not match canonical source root"

if [[ -n "$(git -C "$REPO_ROOT" status --porcelain=v1 --untracked-files=all)" ]]; then
  die "canonical checkout is not clean"
fi

HEAD_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
REQUESTED_SHA="${LIFE_MANAGER_RELEASE_SHA:-$HEAD_SHA}"
[[ "$REQUESTED_SHA" =~ ^[0-9a-f]{40}$ ]] || die "release SHA must be a 40-character lowercase git SHA"
[[ "$REQUESTED_SHA" == "$HEAD_SHA" ]] || die "release SHA must equal canonical checkout HEAD"

HOME_ROOT="${HOME:?HOME must be set}"
DATA_HOME="${LIFE_MANAGER_DATA_HOME:-$HOME_ROOT/.local/share/life-manager}"
STATE_HOME="${LIFE_MANAGER_STATE_HOME:-$HOME_ROOT/.local/state/life-manager}"

AFFILIATE_DATA="$DATA_HOME/affiliate"
RELEASES="$AFFILIATE_DATA/releases"
RELEASE="$RELEASES/$HEAD_SHA"
CURRENT="$AFFILIATE_DATA/current"
AFFILIATE_STATE="$STATE_HOME/affiliate"
mkdir -p "$RELEASES" "$AFFILIATE_STATE"

ARCHIVE_STAGE=""
CURRENT_STAGE=""
RECEIPT_STAGE=""
cleanup() {
  [[ -z "$ARCHIVE_STAGE" || ! -e "$ARCHIVE_STAGE" ]] || rm -rf "$ARCHIVE_STAGE"
  [[ -z "$CURRENT_STAGE" || ! -e "$CURRENT_STAGE" ]] || rm -f "$CURRENT_STAGE"
  [[ -z "$RECEIPT_STAGE" || ! -e "$RECEIPT_STAGE" ]] || rm -f "$RECEIPT_STAGE"
}
trap cleanup EXIT

ARCHIVE_STAGE="$(mktemp -d "$RELEASES/.archive-${HEAD_SHA}.XXXXXX")"
git -C "$REPO_ROOT" archive --format=tar "$HEAD_SHA" -- skills/affiliate \
  | tar -xf - -C "$ARCHIVE_STAGE" --strip-components=2
# Mutable state is never part of an immutable release, even if it is tracked
# by a future source checkout.
[[ ! -d "$ARCHIVE_STAGE/state" ]] || rm -rf "$ARCHIVE_STAGE/state"

if [[ -e "$RELEASE" || -L "$RELEASE" ]]; then
  [[ -d "$RELEASE" && ! -L "$RELEASE" ]] || die "release path exists but is not a directory"
  diff -qr "$ARCHIVE_STAGE" "$RELEASE" >/dev/null \
    || die "existing release for $HEAD_SHA conflicts with canonical source"
  rm -rf "$ARCHIVE_STAGE"
  ARCHIVE_STAGE=""
else
  mv "$ARCHIVE_STAGE" "$RELEASE"
  ARCHIVE_STAGE=""
fi

if [[ -L "$CURRENT" ]]; then
  if [[ "$(readlink "$CURRENT")" != "$RELEASE" ]]; then
    CURRENT_STAGE="$AFFILIATE_DATA/.current-${HEAD_SHA}.$$"
    ln -s "$RELEASE" "$CURRENT_STAGE"
    mv -h -f "$CURRENT_STAGE" "$CURRENT"
    CURRENT_STAGE=""
  fi
elif [[ -e "$CURRENT" ]]; then
  die "current path exists and is not a symlink"
else
  CURRENT_STAGE="$AFFILIATE_DATA/.current-${HEAD_SHA}.$$"
  ln -s "$RELEASE" "$CURRENT_STAGE"
  mv -h -f "$CURRENT_STAGE" "$CURRENT"
  CURRENT_STAGE=""
fi

RECEIPT="$AFFILIATE_STATE/ownership-${HEAD_SHA}.json"
RECEIPT_STAGE="$AFFILIATE_STATE/.ownership-${HEAD_SHA}.$$"
INSTALL_LAUNCHD="${AFFILIATE_INSTALL_LAUNCHD:-1}"
/usr/bin/plutil -create xml1 "$RECEIPT_STAGE"
if [[ "$INSTALL_LAUNCHD" == "1" ]]; then
  /usr/bin/plutil -insert status -string "LOCAL_READY" "$RECEIPT_STAGE"
else
  /usr/bin/plutil -insert status -string "LOCAL_RELEASE_ONLY" "$RECEIPT_STAGE"
fi
/usr/bin/plutil -insert canonical_sha -string "$HEAD_SHA" "$RECEIPT_STAGE"
/usr/bin/plutil -insert release_path -string "$RELEASE" "$RECEIPT_STAGE"
/usr/bin/plutil -insert legacy_source_commit -string \
  "682cc263750934056e743464d77c6bb9ffe027e1" "$RECEIPT_STAGE"
/usr/bin/plutil -insert artifact_hashes -json \
  '["legacy/SHA256SUMS","legacy/DEPENDENCIES.sha256"]' "$RECEIPT_STAGE"
/usr/bin/plutil -insert missing_dependency_inventory -string \
  "publisher and commission reconciliation remain gated" "$RECEIPT_STAGE"
/usr/bin/plutil -insert excluded_mutable_paths -json '["state"]' "$RECEIPT_STAGE"
if [[ "$INSTALL_LAUNCHD" == "1" ]]; then
  /usr/bin/plutil -insert launchd_owners -json \
    '["ai.anicca.affiliate-browser","ai.anicca.affiliate-loop"]' "$RECEIPT_STAGE"
else
  /usr/bin/plutil -insert launchd_owners -array "$RECEIPT_STAGE"
fi
/usr/bin/plutil -convert json "$RECEIPT_STAGE"
if [[ -e "$RECEIPT" ]]; then
  cmp -s "$RECEIPT_STAGE" "$RECEIPT" \
    || die "ownership receipt exists with conflicting content"
  rm -f "$RECEIPT_STAGE"
  RECEIPT_STAGE=""
else
  mv "$RECEIPT_STAGE" "$RECEIPT"
  RECEIPT_STAGE=""
fi

if [[ "$INSTALL_LAUNCHD" != "1" ]]; then
  printf 'installed local affiliate release without launchd %s\n' "$HEAD_SHA"
  exit 0
fi

CLOAK_PYTHON="$HOME_ROOT/.openclaw/skills/_shared/venv-cloak/bin/python"
[[ -x "$CLOAK_PYTHON" ]] || die "CloakBrowser Python is unavailable"
PROFILE_ROOT="$HOME_ROOT/.cloak/profiles/affiliate"
"$CLOAK_PYTHON" "$RELEASE/scripts/profile_provisioner.py" --root "$PROFILE_ROOT" \
  --receipt "$AFFILIATE_STATE/browser-profiles.json"

LAUNCH_AGENTS="$HOME_ROOT/Library/LaunchAgents"
LOG_DIR="$HOME_ROOT/.local/state/life-manager/affiliate/logs"
mkdir -p "$LAUNCH_AGENTS" "$LOG_DIR"
BROWSER_PLIST="$LAUNCH_AGENTS/ai.anicca.affiliate-browser.plist"
LOOP_PLIST="$LAUNCH_AGENTS/ai.anicca.affiliate-loop.plist"
cat > "$BROWSER_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>ai.anicca.affiliate-browser</string>
<key>ProgramArguments</key><array><string>$CLOAK_PYTHON</string><string>$CURRENT/scripts/local_browser.py</string></array>
<key>EnvironmentVariables</key><dict><key>HOME</key><string>$HOME_ROOT</string><key>AFFILIATE_BROWSER_PROFILE</key><string>$PROFILE_ROOT/en</string><key>AFFILIATE_CDP_PORT</key><string>9324</string></dict>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>ThrottleInterval</key><integer>30</integer>
<key>StandardOutPath</key><string>$LOG_DIR/browser.out.log</string><key>StandardErrorPath</key><string>$LOG_DIR/browser.err.log</string>
</dict></plist>
EOF
cat > "$LOOP_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>ai.anicca.affiliate-loop</string>
<key>ProgramArguments</key><array><string>/bin/sh</string><string>$CURRENT/affiliate</string><string>loop</string><string>wake</string></array>
<key>EnvironmentVariables</key><dict><key>HOME</key><string>$HOME_ROOT</string><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
<key>RunAtLoad</key><true/><key>StartInterval</key><integer>600</integer><key>ThrottleInterval</key><integer>60</integer>
<key>StandardOutPath</key><string>$LOG_DIR/loop.out.log</string><key>StandardErrorPath</key><string>$LOG_DIR/loop.err.log</string>
</dict></plist>
EOF
/usr/bin/plutil -lint "$BROWSER_PLIST" "$LOOP_PLIST" >/dev/null
for label in ai.anicca.affiliate-loop ai.anicca.affiliate-browser; do
  /bin/launchctl bootout "gui/$(id -u)/$label" >/dev/null 2>&1 || true
done
/bin/launchctl bootstrap "gui/$(id -u)" "$BROWSER_PLIST"
/bin/launchctl bootstrap "gui/$(id -u)" "$LOOP_PLIST"

printf 'installed local affiliate release %s\n' "$HEAD_SHA"
