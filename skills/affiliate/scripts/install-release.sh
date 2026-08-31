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
REQUESTED_SHA="${MR_BOT_RELEASE_SHA:-$HEAD_SHA}"
[[ "$REQUESTED_SHA" =~ ^[0-9a-f]{40}$ ]] || die "release SHA must be a 40-character lowercase git SHA"
[[ "$REQUESTED_SHA" == "$HEAD_SHA" ]] || die "release SHA must equal canonical checkout HEAD"

HOME_ROOT="${HOME:?HOME must be set}"
DATA_HOME="${MR_BOT_DATA_HOME:-$HOME_ROOT/.local/share/mr-bot}"
STATE_HOME="${MR_BOT_STATE_HOME:-$HOME_ROOT/.local/state/mr-bot}"

if [[ -n "${AFFILIATE_CANONICAL_HOME:-}" ]]; then
  CANONICAL_HOME="$AFFILIATE_CANONICAL_HOME"
else
  CANONICAL_HOME="$(/usr/bin/python3 -I -c 'import os,pwd; print(pwd.getpwuid(os.getuid()).pw_dir)')" \
    || die "canonical OS home is unavailable"
fi
[[ "$CANONICAL_HOME" = /* && -d "$CANONICAL_HOME" ]] \
  || die "canonical OS home is invalid"
GUARD_PATH="$CANONICAL_HOME/gig/releases/mr-bot/current/skills/earn/gig/scripts/gig_disk_guard.py"
[[ -f "$GUARD_PATH" && ! -L "$GUARD_PATH" && -r "$GUARD_PATH" ]] \
  || die "Mr.bot disk guard is unavailable at $GUARD_PATH"
GUARD_COMPILE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mr-bot-disk-guard.XXXXXX")" \
  || die "Mr.bot disk guard compile staging failed"
GUARD_COMPILE_PATH="$GUARD_COMPILE_DIR/gig_disk_guard.py"
if ! cp "$GUARD_PATH" "$GUARD_COMPILE_PATH" \
  || ! /usr/bin/python3 -I -m py_compile "$GUARD_COMPILE_PATH"; then
  rm -rf "$GUARD_COMPILE_DIR"
  die "Mr.bot disk guard failed py_compile"
fi
rm -rf "$GUARD_COMPILE_DIR"
GUARD_COMPILE_DIR=""
GUARD_SHA256="$(/usr/bin/shasum -a 256 "$GUARD_PATH" | /usr/bin/awk '{print $1}')" \
  || die "Mr.bot disk guard sha256 failed"
[[ "$GUARD_SHA256" =~ ^[[:xdigit:]]{64}$ ]] \
  || die "Mr.bot disk guard sha256 is invalid"

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
/usr/bin/plutil -insert disk_guard_path -string "$GUARD_PATH" "$RECEIPT_STAGE"
/usr/bin/plutil -insert disk_guard_sha256 -string "$GUARD_SHA256" "$RECEIPT_STAGE"
/usr/bin/plutil -insert external_dependencies -array "$RECEIPT_STAGE"
/usr/bin/plutil -insert external_dependencies.0 -dictionary "$RECEIPT_STAGE"
/usr/bin/plutil -insert external_dependencies.0.name -string \
  "mr-bot-disk-guard" "$RECEIPT_STAGE"
/usr/bin/plutil -insert external_dependencies.0.path -string \
  "$GUARD_PATH" "$RECEIPT_STAGE"
/usr/bin/plutil -insert external_dependencies.0.sha256 -string \
  "$GUARD_SHA256" "$RECEIPT_STAGE"
/usr/bin/plutil -insert excluded_mutable_paths -json '["state"]' "$RECEIPT_STAGE"
if [[ "$INSTALL_LAUNCHD" == "1" ]]; then
  /usr/bin/plutil -insert launchd_owners -json \
    '["ai.anicca.affiliate-browser","ai.anicca.affiliate-impact-browser","ai.anicca.affiliate-x-browser","ai.anicca.affiliate-source-refresh","ai.anicca.affiliate-composition","ai.anicca.affiliate-loop"]' "$RECEIPT_STAGE"
  /usr/bin/plutil -insert deferred_launchd_owners -json '[]' "$RECEIPT_STAGE"
else
  /usr/bin/plutil -insert launchd_owners -array "$RECEIPT_STAGE"
  /usr/bin/plutil -insert deferred_launchd_owners -json \
    '["ai.anicca.affiliate-browser","ai.anicca.affiliate-impact-browser","ai.anicca.affiliate-x-browser"]' \
    "$RECEIPT_STAGE"
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
LOG_DIR="$HOME_ROOT/.local/state/mr-bot/affiliate/logs"
mkdir -p "$LAUNCH_AGENTS" "$LOG_DIR"
BROWSER_PLIST="$LAUNCH_AGENTS/ai.anicca.affiliate-browser.plist"
IMPACT_BROWSER_PLIST="$LAUNCH_AGENTS/ai.anicca.affiliate-impact-browser.plist"
X_BROWSER_PLIST="$LAUNCH_AGENTS/ai.anicca.affiliate-x-browser.plist"
LOOP_PLIST="$LAUNCH_AGENTS/ai.anicca.affiliate-loop.plist"
SOURCE_PLIST="$LAUNCH_AGENTS/ai.anicca.affiliate-source-refresh.plist"
COMPOSITION_PLIST="$LAUNCH_AGENTS/ai.anicca.affiliate-composition.plist"
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
cat > "$IMPACT_BROWSER_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>ai.anicca.affiliate-impact-browser</string>
<key>ProgramArguments</key><array><string>$CLOAK_PYTHON</string><string>$CURRENT/scripts/local_browser.py</string></array>
<key>EnvironmentVariables</key><dict><key>HOME</key><string>$HOME_ROOT</string><key>AFFILIATE_BROWSER_PROFILE</key><string>$PROFILE_ROOT/impact-en</string><key>AFFILIATE_CDP_PORT</key><string>9327</string><key>AFFILIATE_START_URL</key><string>https://app.impact.com/login.user</string></dict>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>ThrottleInterval</key><integer>30</integer>
<key>StandardOutPath</key><string>$LOG_DIR/impact-browser.out.log</string><key>StandardErrorPath</key><string>$LOG_DIR/impact-browser.err.log</string>
</dict></plist>
EOF
cat > "$X_BROWSER_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>ai.anicca.affiliate-x-browser</string>
<key>ProgramArguments</key><array><string>$CLOAK_PYTHON</string><string>$CURRENT/scripts/local_browser.py</string></array>
<key>EnvironmentVariables</key><dict><key>HOME</key><string>$HOME_ROOT</string><key>AFFILIATE_BROWSER_PROFILE</key><string>$PROFILE_ROOT/x-en</string><key>AFFILIATE_CDP_PORT</key><string>9326</string><key>AFFILIATE_START_URL</key><string>https://x.com/home</string></dict>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>ThrottleInterval</key><integer>30</integer>
<key>StandardOutPath</key><string>$LOG_DIR/x-browser.out.log</string><key>StandardErrorPath</key><string>$LOG_DIR/x-browser.err.log</string>
</dict></plist>
EOF
cat > "$LOOP_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>ai.anicca.affiliate-loop</string>
<key>ProgramArguments</key><array><string>/bin/sh</string><string>$CURRENT/affiliate</string><string>loop</string><string>wake</string></array>
<key>EnvironmentVariables</key><dict><key>HOME</key><string>$HOME_ROOT</string><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string><key>AFFILIATE_LANDING_ROOT</key><string>${AFFILIATE_LANDING_ROOT:-$HOME_ROOT/anicca-project/.worktrees/affiliate-foundation-prod}</string><key>AFFILIATE_REPOST_STATE_DIR</key><string>${AFFILIATE_REPOST_STATE_DIR:-$HOME_ROOT/loops/x-repost}</string></dict>
<key>RunAtLoad</key><true/><key>StartInterval</key><integer>600</integer><key>ThrottleInterval</key><integer>60</integer>
<key>StandardOutPath</key><string>$LOG_DIR/loop.out.log</string><key>StandardErrorPath</key><string>$LOG_DIR/loop.err.log</string>
</dict></plist>
EOF
cat > "$SOURCE_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>ai.anicca.affiliate-source-refresh</string>
<key>ProgramArguments</key><array><string>/bin/sh</string><string>$CURRENT/affiliate</string><string>sources</string><string>wake</string></array>
<key>EnvironmentVariables</key><dict><key>HOME</key><string>$HOME_ROOT</string><key>PATH</key><string>$HOME_ROOT/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
<key>RunAtLoad</key><true/><key>StartInterval</key><integer>600</integer><key>ThrottleInterval</key><integer>60</integer>
<key>StandardOutPath</key><string>$LOG_DIR/source-refresh.out.log</string><key>StandardErrorPath</key><string>$LOG_DIR/source-refresh.err.log</string>
</dict></plist>
EOF
cat > "$COMPOSITION_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>ai.anicca.affiliate-composition</string>
<key>ProgramArguments</key><array><string>/bin/sh</string><string>$CURRENT/affiliate</string><string>compose</string><string>wake</string></array>
<key>EnvironmentVariables</key><dict><key>HOME</key><string>$HOME_ROOT</string><key>PATH</key><string>$HOME_ROOT/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
<key>RunAtLoad</key><true/><key>StartInterval</key><integer>600</integer><key>ThrottleInterval</key><integer>60</integer>
<key>StandardOutPath</key><string>$LOG_DIR/composition.out.log</string><key>StandardErrorPath</key><string>$LOG_DIR/composition.err.log</string>
</dict></plist>
EOF
/usr/bin/plutil -lint "$BROWSER_PLIST" "$IMPACT_BROWSER_PLIST" "$X_BROWSER_PLIST" "$SOURCE_PLIST" "$COMPOSITION_PLIST" "$LOOP_PLIST" >/dev/null

bootstrap_agent() {
  local plist="$1"
  local attempt
  for attempt in {1..10}; do
    if /bin/launchctl bootstrap "gui/$(id -u)" "$plist" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  die "launchd bootstrap failed for $(basename "$plist")"
}

ensure_agent() {
  local label="$1"
  local plist="$2"
  if /bin/launchctl print "gui/$(id -u)/$label" >/dev/null 2>&1; then
    return 0
  fi
  bootstrap_agent "$plist"
}

ensure_agent "ai.anicca.affiliate-browser" "$BROWSER_PLIST"
for attempt in {1..30}; do
  if /usr/bin/curl -fsS --max-time 2 "http://127.0.0.1:9324/json/version" >/dev/null 2>&1; then
    break
  fi
  [[ "$attempt" != "30" ]] || die "affiliate browser CDP did not become ready"
  sleep 1
done
ensure_agent "ai.anicca.affiliate-impact-browser" "$IMPACT_BROWSER_PLIST"
for attempt in {1..30}; do
  if /usr/bin/curl -fsS --max-time 2 "http://127.0.0.1:9327/json/version" >/dev/null 2>&1; then
    break
  fi
  [[ "$attempt" != "30" ]] || die "affiliate Impact browser CDP did not become ready"
  sleep 1
done
ensure_agent "ai.anicca.affiliate-x-browser" "$X_BROWSER_PLIST"
for attempt in {1..30}; do
  if /usr/bin/curl -fsS --max-time 2 "http://127.0.0.1:9326/json/version" >/dev/null 2>&1; then
    break
  fi
  [[ "$attempt" != "30" ]] || die "affiliate X browser CDP did not become ready"
  sleep 1
done
ensure_agent "ai.anicca.affiliate-source-refresh" "$SOURCE_PLIST"
ensure_agent "ai.anicca.affiliate-composition" "$COMPOSITION_PLIST"
ensure_agent "ai.anicca.affiliate-loop" "$LOOP_PLIST"

printf 'installed local affiliate release %s\n' "$HEAD_SHA"
