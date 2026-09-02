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
LABEL="ai.anicca.lancers-revenue-application"
REPORT_LABEL="ai.anicca.lancers-revenue-telegram-report"
WORK_SYNC_LABEL="ai.anicca.lancers-revenue-work-sync"
STOREFRONT_LABEL="ai.anicca.lancers-revenue-storefront"
BROWSER_LABEL="ai.anicca.lancers-revenue-browser"
RUNTIME_PATH="${LANCERS_RUNTIME_PATH:-${HOME}/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin}"

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
PLIST_TEMP=""
REPORT_PLIST_TEMP=""
WORK_SYNC_PLIST_TEMP=""
STOREFRONT_PLIST_TEMP=""
BROWSER_PLIST_TEMP=""

cleanup() {
  [[ -z "$PLIST_TEMP" || ! -e "$PLIST_TEMP" ]] || rm -f "$PLIST_TEMP"
  [[ -z "$REPORT_PLIST_TEMP" || ! -e "$REPORT_PLIST_TEMP" ]] || rm -f "$REPORT_PLIST_TEMP"
  [[ -z "$WORK_SYNC_PLIST_TEMP" || ! -e "$WORK_SYNC_PLIST_TEMP" ]] || rm -f "$WORK_SYNC_PLIST_TEMP"
  [[ -z "$STOREFRONT_PLIST_TEMP" || ! -e "$STOREFRONT_PLIST_TEMP" ]] || rm -f "$STOREFRONT_PLIST_TEMP"
  [[ -z "$BROWSER_PLIST_TEMP" || ! -e "$BROWSER_PLIST_TEMP" ]] || rm -f "$BROWSER_PLIST_TEMP"
  [[ ! -e "$STAGING" ]] || rm -rf "$STAGING"
  [[ ! -e "$CHECK_ROOT" ]] || rm -rf "$CHECK_ROOT"
}
trap cleanup EXIT

git -C "$REPO_ROOT" archive --format=tar "$RELEASE_SHA" \
  skills/earn/lancers/SKILL.md \
  skills/earn/lancers/products/monthly-sns-content-ops-v1.json \
  skills/earn/lancers/assets/monthly-sns-content-ops-v1.png \
  skills/gig-work/profile/avatar.jpg \
  skills/earn/lancers/scripts/storefront_offer.py \
  skills/earn/lancers/scripts/application_loop.py \
  skills/earn/lancers/scripts/application_tick.py \
  skills/earn/lancers/scripts/work_sync.py \
  skills/earn/lancers/scripts/status.py \
  skills/earn/lancers/scripts/lancers_adapter.py \
  skills/_shared/marketplace-core/scripts/application_transaction.py \
  skills/_shared/marketplace-core/scripts/contracts.py \
  skills/_shared/marketplace-core/scripts/ledger.py \
  skills/_shared/marketplace-core/schemas/event.schema.json \
  skills/_shared/marketplace-core/schemas/opportunity.schema.json \
  skills/_shared/marketplace-core/schemas/payment.schema.json \
  skills/gig-work/schemas/application_decisions.schema.json \
  skills/gig-work/schemas/reply_composition.schema.json \
  runtime/agent-runner/agent_runner.py \
  runtime/agent-runner/config.json \
  runtime/agent-runner/token_budget.py \
  runtime/loop/macos_loop_registry.py \
  runtime/loop/runtime_event.py | tar -xf - -C "$STAGING"
git -C "$REPO_ROOT" archive --format=tar "$RELEASE_SHA" \
  skills/earn/lancers/scripts/telegram_report.py \
  skills/_shared/marketplace-core/scripts/telegram_outbox.py | tar -xf - -C "$STAGING"
chmod 755 "$STAGING/runtime/agent-runner/agent_runner.py"

PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" - "$STAGING" "$CHECK_ROOT" <<'PY'
import importlib.util
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
sys.dont_write_bytecode = True
loop_path = root / "skills/earn/lancers/scripts/application_loop.py"
spec = importlib.util.spec_from_file_location("lancers_release_application_loop_check", loop_path)
if spec is None or spec.loader is None:
    raise RuntimeError("application_loop_import_unavailable")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
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
TEMPLATE="$SCRIPT_DIR/../launchd/$LABEL.plist"
PLIST_PATH="$LAUNCH_AGENT_DIR/$LABEL.plist"
PLIST_TEMP="$(mktemp "$LAUNCH_AGENT_DIR/.${LABEL}.plist.XXXXXX")"

# Write through a same-directory temporary so the final plist replacement is atomic.
"$PYTHON_BIN" - "$TEMPLATE" "$PLIST_TEMP" "$PYTHON_BIN" \
  "$RELEASE_PATH/skills/earn/lancers/scripts/application_loop.py" \
  "$STATE_ROOT/application.json" "$STATE_ROOT/logs/application.out.log" \
  "$STATE_ROOT/logs/application.err.log" "$RELEASE_PATH" "$INSTALL_MODE" "$RUNTIME_PATH" <<'PY'
import os
import plistlib
import sys
from pathlib import Path

template, output, python_bin, loop_path, state_path, stdout_path, stderr_path, working_dir, mode, runtime_path = sys.argv[1:]
value = plistlib.loads(Path(template).read_bytes())
arguments = [python_bin, loop_path, "--json"]
if mode == "reconcile-only":
    arguments.append("--reconcile-only")
else:
    arguments.append("--exhaustive")
arguments.extend(("--state-path", state_path))
value["ProgramArguments"] = arguments
value["WorkingDirectory"] = working_dir
value["StandardOutPath"] = stdout_path
value["StandardErrorPath"] = stderr_path
value["EnvironmentVariables"]["PATH"] = runtime_path
Path(output).write_bytes(plistlib.dumps(value, fmt=plistlib.FMT_XML, sort_keys=False))
os.chmod(output, 0o644)
PY
mv -f "$PLIST_TEMP" "$PLIST_PATH"
PLIST_TEMP=""
"$PLUTIL_BIN" -lint "$PLIST_PATH" >/dev/null

WORK_SYNC_TEMPLATE="$SCRIPT_DIR/../launchd/$WORK_SYNC_LABEL.plist"
WORK_SYNC_PLIST_PATH="$LAUNCH_AGENT_DIR/$WORK_SYNC_LABEL.plist"
WORK_SYNC_PLIST_TEMP="$(mktemp "$LAUNCH_AGENT_DIR/.${WORK_SYNC_LABEL}.plist.XXXXXX")"
"$PYTHON_BIN" - "$WORK_SYNC_TEMPLATE" "$WORK_SYNC_PLIST_TEMP" "$PYTHON_BIN" \
  "$RELEASE_PATH/skills/earn/lancers/scripts/work_sync.py" "$STATE_ROOT/work-sync.json" \
  "$STATE_ROOT/logs/work-sync.out.log" "$STATE_ROOT/logs/work-sync.err.log" \
  "$RELEASE_PATH" "$RUNTIME_PATH" <<'PY'
import os, plistlib, sys
from pathlib import Path
template, output, python_bin, work_sync, state, stdout, stderr, release, runtime = sys.argv[1:]
value = plistlib.loads(Path(template).read_bytes())
value["ProgramArguments"] = [python_bin, work_sync, "--json", "--state-path", state]
value["WorkingDirectory"] = release; value["StandardOutPath"] = stdout; value["StandardErrorPath"] = stderr
value["EnvironmentVariables"]["PATH"] = runtime
Path(output).write_bytes(plistlib.dumps(value, fmt=plistlib.FMT_XML, sort_keys=False)); os.chmod(output, 0o644)
PY
mv -f "$WORK_SYNC_PLIST_TEMP" "$WORK_SYNC_PLIST_PATH"
WORK_SYNC_PLIST_TEMP=""
"$PLUTIL_BIN" -lint "$WORK_SYNC_PLIST_PATH" >/dev/null

STOREFRONT_TEMPLATE="$SCRIPT_DIR/../launchd/$STOREFRONT_LABEL.plist"
STOREFRONT_PLIST_PATH="$LAUNCH_AGENT_DIR/$STOREFRONT_LABEL.plist"
STOREFRONT_PLIST_TEMP="$(mktemp "$LAUNCH_AGENT_DIR/.${STOREFRONT_LABEL}.plist.XXXXXX")"
"$PYTHON_BIN" - "$STOREFRONT_TEMPLATE" "$STOREFRONT_PLIST_TEMP" "$PYTHON_BIN" \
  "$RELEASE_PATH/skills/earn/lancers/scripts/storefront_offer.py" \
  "$RELEASE_PATH/skills/earn/lancers/products/monthly-sns-content-ops-v1.json" \
  "$STATE_ROOT/application.json" "$STATE_ROOT/logs/storefront.stdout.log" \
  "$STATE_ROOT/logs/storefront.stderr.log" "$RELEASE_PATH" "$RUNTIME_PATH" <<'PY'
import os, plistlib, sys
from pathlib import Path
template, output, python_bin, storefront, product, state, stdout, stderr, release, runtime = sys.argv[1:]
value = plistlib.loads(Path(template).read_bytes())
value["ProgramArguments"] = [python_bin, storefront, "--apply", "--product", product, "--state-path", state]
value["WorkingDirectory"] = release; value["StandardOutPath"] = stdout; value["StandardErrorPath"] = stderr
value["EnvironmentVariables"]["PATH"] = runtime
Path(output).write_bytes(plistlib.dumps(value, fmt=plistlib.FMT_XML, sort_keys=False)); os.chmod(output, 0o644)
PY
mv -f "$STOREFRONT_PLIST_TEMP" "$STOREFRONT_PLIST_PATH"
STOREFRONT_PLIST_TEMP=""
"$PLUTIL_BIN" -lint "$STOREFRONT_PLIST_PATH" >/dev/null

REPORT_TEMPLATE="$SCRIPT_DIR/../launchd/$REPORT_LABEL.plist"
REPORT_PLIST_PATH="$LAUNCH_AGENT_DIR/$REPORT_LABEL.plist"
REPORT_PLIST_TEMP="$(mktemp "$LAUNCH_AGENT_DIR/.${REPORT_LABEL}.plist.XXXXXX")"
"$PYTHON_BIN" - "$REPORT_TEMPLATE" "$REPORT_PLIST_TEMP" "$PYTHON_BIN" \
  "$RELEASE_PATH/skills/earn/lancers/scripts/telegram_report.py" "$RELEASE_PATH" \
  "$STATE_ROOT/telegram.sqlite3" "$STATE_ROOT/marketplace-ledger.sqlite3" \
  "$STATE_ROOT/application.json" "$STATE_ROOT/logs/application.out.log" \
  "$STATE_ROOT/logs/storefront.stdout.log" "$STATE_ROOT/logs/telegram-report.stdout.log" \
  "$STATE_ROOT/logs/telegram-report.stderr.log" "$RUNTIME_PATH" <<'PY'
import os, plistlib, sys
from pathlib import Path
template, output, python_bin, reporter, release, database, ledger, state, application_log, storefront_log, stdout, stderr, runtime = sys.argv[1:]
value = plistlib.loads(Path(template).read_bytes())
value["ProgramArguments"] = [python_bin, reporter, "--json", "--database", database, "--ledger-database", ledger, "--state-path", state, "--application-log", application_log, "--storefront-log", storefront_log]
value["WorkingDirectory"] = release; value["StandardOutPath"] = stdout; value["StandardErrorPath"] = stderr; value["EnvironmentVariables"]["PATH"] = runtime
Path(output).write_bytes(plistlib.dumps(value, fmt=plistlib.FMT_XML, sort_keys=False)); os.chmod(output, 0o644)
PY
mv -f "$REPORT_PLIST_TEMP" "$REPORT_PLIST_PATH"
REPORT_PLIST_TEMP=""
"$PLUTIL_BIN" -lint "$REPORT_PLIST_PATH" >/dev/null

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
value["ProgramArguments"] = [chromium, "--no-first-run", "--no-default-browser-check", "--remote-debugging-address=127.0.0.1", "--remote-allow-origins=*", "--remote-debugging-port=9227", "--disk-cache-size=67108864", "--media-cache-size=33554432", f"--disk-cache-dir={Path.home() / '.cache/lancers-revenue-browser'}", f"--user-data-dir={profile}", "about:blank"]
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
  activate_owner "$LABEL" "$PLIST_PATH" "$RELEASE_PATH/skills/earn/lancers/scripts/application_loop.py"
  activate_owner "$REPORT_LABEL" "$REPORT_PLIST_PATH" "$RELEASE_PATH/skills/earn/lancers/scripts/telegram_report.py"
  activate_owner "$WORK_SYNC_LABEL" "$WORK_SYNC_PLIST_PATH" "$RELEASE_PATH/skills/earn/lancers/scripts/work_sync.py"
  activate_owner "$STOREFRONT_LABEL" "$STOREFRONT_PLIST_PATH" "$RELEASE_PATH/skills/earn/lancers/scripts/storefront_offer.py"
fi

INSTALLED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
"$PYTHON_BIN" - "$STATE_ROOT/deployment.json" "$RELEASE_PATH" "$RELEASE_SHA" \
  "$INSTALL_MODE" "$INSTALLED_AT" "$LABEL" "$REPORT_LABEL" "$WORK_SYNC_LABEL" "$STOREFRONT_LABEL" "$BROWSER_LABEL" <<'PY'
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

manifest_path, release_path, deployed_sha, mode, installed_at, label, report_label, work_sync_label, storefront_label, browser_label = sys.argv[1:]
release = Path(release_path)
files = {}
for path in sorted(path for path in release.rglob("*") if path.is_file()):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    files[path.relative_to(release).as_posix()] = digest
manifest = {
    "deployed_sha": deployed_sha,
    "files": files,
    "installed_at": installed_at,
    "launchd_label": label,
    "report_launchd_label": report_label,
    "work_sync_launchd_label": work_sync_label,
    "storefront_launchd_label": storefront_label,
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
