#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
REPO_ROOT="${SCRIPT_DIR:h:h:h}"
RELEASE_SHA="${LANCERS_RELEASE_SHA:?LANCERS_RELEASE_SHA is required}"
INSTALL_ROOT="${LANCERS_INSTALL_ROOT:?LANCERS_INSTALL_ROOT is required}"
LAUNCH_AGENT_DIR="${LANCERS_LAUNCH_AGENT_DIR:?LANCERS_LAUNCH_AGENT_DIR is required}"
STATE_ROOT="${LANCERS_STATE_ROOT:?LANCERS_STATE_ROOT is required}"
INSTALL_MODE="${LANCERS_INSTALL_MODE:?LANCERS_INSTALL_MODE is required}"
ACTIVATE="${LANCERS_ACTIVATE:?LANCERS_ACTIVATE is required}"
BROWSER_LABEL="ai.anicca.lancers-revenue-browser"

fail() {
  print -u2 -- "install-local: $1"
  exit 1
}

[[ "$INSTALL_MODE" == "reconcile-only" || "$INSTALL_MODE" == "normal" ]] \
  || fail "LANCERS_INSTALL_MODE must be reconcile-only or normal"
[[ "$ACTIVATE" == "0" || "$ACTIVATE" == "1" ]] \
  || fail "LANCERS_ACTIVATE must be 0 or 1"
[[ "$RELEASE_SHA" =~ '^[0-9a-f]{40}$' ]] || fail "LANCERS_RELEASE_SHA must be a full commit SHA"

if [[ "${LANCERS_SKIP_MAIN_ASSERT:-0}" != "1" ]]; then
  HEAD_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
  [[ "$RELEASE_SHA" == "$HEAD_SHA" ]] || fail "release SHA is not repository HEAD"
  [[ -z "$(git -C "$REPO_ROOT" status --porcelain)" ]] || fail "repository is not clean"
  git -C "$REPO_ROOT" rev-parse --verify origin/main^{commit} >/dev/null \
    || fail "origin/main is unavailable"
  git -C "$REPO_ROOT" merge-base --is-ancestor "$RELEASE_SHA" origin/main \
    || fail "release SHA is not reachable from origin/main"
fi
git -C "$REPO_ROOT" cat-file -e "$RELEASE_SHA^{commit}" \
  || fail "release SHA is not a commit"

PYTHON_BIN="${LANCERS_PYTHON:-$(command -v python3)}"
[[ -x "$PYTHON_BIN" ]] || fail "python3 is unavailable"
PLUTIL_BIN="${LANCERS_PLUTIL:-$(command -v plutil || true)}"
[[ -n "$PLUTIL_BIN" && -x "$PLUTIL_BIN" ]] || fail "plutil is unavailable"

RELEASES_ROOT="$INSTALL_ROOT/releases"
mkdir -p "$RELEASES_ROOT"
chmod 700 "$INSTALL_ROOT" "$RELEASES_ROOT"
STAGING="$(mktemp -d "$RELEASES_ROOT/.${RELEASE_SHA}.staging.XXXXXX")"
CHECK_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/lancers-install-check.XXXXXX")"
BROWSER_PLIST_TEMP=""

cleanup() {
  [[ -z "$BROWSER_PLIST_TEMP" || ! -e "$BROWSER_PLIST_TEMP" ]] || rm -f "$BROWSER_PLIST_TEMP"
  [[ ! -e "$STAGING" ]] || rm -rf "$STAGING"
  [[ ! -e "$CHECK_ROOT" ]] || rm -rf "$CHECK_ROOT"
}
trap cleanup EXIT

git -C "$REPO_ROOT" archive --format=tar "$RELEASE_SHA" \
  skills/earn/lancers/SKILL.md | tar -xf - -C "$STAGING"

PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" - "$STAGING" "$CHECK_ROOT" <<'PY'
import py_compile
import sys
from pathlib import Path

root = Path(sys.argv[1])
check_root = Path(sys.argv[2])
python_files = sorted(root.rglob("*.py"))
for index, path in enumerate(python_files):
    py_compile.compile(
        str(path),
        cfile=str(check_root / f"{index}.pyc"),
        doraise=True,
    )
PY

RELEASE_PATH="$RELEASES_ROOT/$RELEASE_SHA"
if [[ -e "$RELEASE_PATH" ]]; then
  [[ -d "$RELEASE_PATH" && ! -L "$RELEASE_PATH" ]] \
    || fail "existing release path is not a directory"
  if ! "$PYTHON_BIN" - "$STAGING" "$RELEASE_PATH" <<'PY'
import sys
from pathlib import Path

left, right = (Path(value) for value in sys.argv[1:])
def files(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )

left_files = files(left)
right_files = files(right)
if left_files != right_files:
    raise SystemExit(1)
for relative in left_files:
    if (left / relative).read_bytes() != (right / relative).read_bytes():
        raise SystemExit(1)
PY
  then
    fail "existing release has different bytes"
  fi
else
  mv "$STAGING" "$RELEASE_PATH"
fi
find "$RELEASE_PATH" -type d -exec chmod a-w {} +
find "$RELEASE_PATH" -type f -exec chmod a-w {} +

mkdir -p "$LAUNCH_AGENT_DIR" "$STATE_ROOT/logs"
chmod 700 "$LAUNCH_AGENT_DIR" "$STATE_ROOT" "$STATE_ROOT/logs"
CHROMIUM_BIN="${LANCERS_CHROMIUM_BIN:-$(ls -d "$HOME"/.cloakbrowser/chromium-*/Chromium.app/Contents/MacOS/Chromium(N) | sort -V | tail -1)}"
[[ -x "$CHROMIUM_BIN" ]] || fail "CloakBrowser Chromium is unavailable"
BROWSER_TEMPLATE="$SCRIPT_DIR/../launchd/$BROWSER_LABEL.plist"
BROWSER_PLIST_PATH="$LAUNCH_AGENT_DIR/$BROWSER_LABEL.plist"
BROWSER_PLIST_TEMP="$(mktemp "$LAUNCH_AGENT_DIR/.${BROWSER_LABEL}.plist.XXXXXX")"
"$PYTHON_BIN" - "$BROWSER_TEMPLATE" "$BROWSER_PLIST_TEMP" "$CHROMIUM_BIN" \
  "$STATE_ROOT/browser-profile" "$STATE_ROOT/logs/browser.out.log" \
  "$STATE_ROOT/logs/browser.err.log" "$RELEASE_PATH" <<'PY'
import os, plistlib, sys
from pathlib import Path
template, output, chromium, profile, stdout, stderr, release = sys.argv[1:]
value = plistlib.loads(Path(template).read_bytes())
value["ProgramArguments"] = [chromium, "--no-first-run", "--no-default-browser-check", "--remote-debugging-address=127.0.0.1", "--remote-allow-origins=*", "--remote-debugging-port=9227", f"--user-data-dir={profile}", "about:blank"]
value["WorkingDirectory"] = release; value["StandardOutPath"] = stdout; value["StandardErrorPath"] = stderr
Path(output).write_bytes(plistlib.dumps(value, fmt=plistlib.FMT_XML, sort_keys=False)); os.chmod(output, 0o644)
PY
mv -f "$BROWSER_PLIST_TEMP" "$BROWSER_PLIST_PATH"
BROWSER_PLIST_TEMP=""
"$PLUTIL_BIN" -lint "$BROWSER_PLIST_PATH" >/dev/null

if [[ "$ACTIVATE" == "1" ]]; then
  LAUNCHCTL_BIN="${LANCERS_LAUNCHCTL:-$(command -v launchctl || true)}"
  [[ -n "$LAUNCHCTL_BIN" && -x "$LAUNCHCTL_BIN" ]] || fail "launchctl is unavailable"
  DOMAIN="gui/$(id -u)"
  activate_owner() {
    local label="$1" plist="$2" program="$3"
    local target="$DOMAIN/$label" loaded arguments working attempt
    "$LAUNCHCTL_BIN" enable "$target"
    if loaded="$("$LAUNCHCTL_BIN" print "$target" 2>&1)"; then
      "$LAUNCHCTL_BIN" bootout "$target"
      for attempt in {1..40}; do
        "$LAUNCHCTL_BIN" print "$target" >/dev/null 2>&1 || break
        sleep 0.1
      done
      "$LAUNCHCTL_BIN" print "$target" >/dev/null 2>&1 && fail "$label did not boot out"
    elif [[ "$loaded" != *"Could not find service \"$label\" in domain for user gui:"* ]]; then
      fail "$label loaded-state check failed"
    fi
    "$LAUNCHCTL_BIN" bootstrap "$DOMAIN" "$plist"
    loaded="$("$LAUNCHCTL_BIN" print "$target")"
    arguments="$(print -r -- "$loaded" | awk '/^[[:space:]]*arguments = \{$/{found=1; next} found && /^[[:space:]]*\}$/{exit} found{sub(/^[[:space:]]*/, ""); print}')"
    working="$(print -r -- "$loaded" | awk -F' = ' '/^[[:space:]]*working directory = /{print $2; exit}')"
    print -r -- "$arguments" | grep -Fqx -- "$program" || fail "$label does not run the exact release program"
    [[ "$working" == "$RELEASE_PATH" ]] || fail "$label does not use the exact release working directory"
  }
  activate_owner "$BROWSER_LABEL" "$BROWSER_PLIST_PATH" "$CHROMIUM_BIN"
fi

INSTALLED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
"$PYTHON_BIN" - "$STATE_ROOT/deployment.json" "$RELEASE_PATH" "$RELEASE_SHA" \
  "$INSTALL_MODE" "$INSTALLED_AT" "$BROWSER_LABEL" <<'PY'
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

manifest_path, release_path, deployed_sha, mode, installed_at, browser_label = sys.argv[1:]
release = Path(release_path)
files = {}
for path in sorted(path for path in release.rglob("*") if path.is_file()):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    files[path.relative_to(release).as_posix()] = digest
manifest = {
    "deployed_sha": deployed_sha,
    "files": files,
    "installed_at": installed_at,
    "browser_launchd_label": browser_label,
    "mode": mode,
}
target = Path(manifest_path)
fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
try:
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, target)
    os.chmod(target, 0o600)
finally:
    try:
        os.unlink(temporary)
    except FileNotFoundError:
        pass
PY
