#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
REPO_ROOT="${SCRIPT_DIR:h:h:h}"
RELEASE_SHA="${LANCERS_RELEASE_SHA:?LANCERS_RELEASE_SHA is required}"
INSTALL_ROOT="${LANCERS_INSTALL_ROOT:?LANCERS_INSTALL_ROOT is required}"
LAUNCH_AGENT_DIR="${LANCERS_LAUNCH_AGENT_DIR:?LANCERS_LAUNCH_AGENT_DIR is required}"
STATE_ROOT="${LANCERS_STATE_ROOT:?LANCERS_STATE_ROOT is required}"
INSTALL_MODE="${LANCERS_INSTALL_MODE:?LANCERS_INSTALL_MODE is required}"
LABEL="ai.anicca.lancers-revenue-application"
RUNTIME_PATH="${LANCERS_RUNTIME_PATH:-${HOME}/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin}"

fail() {
  print -u2 -- "install-local: $1"
  exit 1
}

[[ "$INSTALL_MODE" == "reconcile-only" || "$INSTALL_MODE" == "normal" ]] \
  || fail "LANCERS_INSTALL_MODE must be reconcile-only or normal"
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

cleanup() {
  [[ -z "$PLIST_TEMP" || ! -e "$PLIST_TEMP" ]] || rm -f "$PLIST_TEMP"
  [[ ! -e "$STAGING" ]] || rm -rf "$STAGING"
  [[ ! -e "$CHECK_ROOT" ]] || rm -rf "$CHECK_ROOT"
}
trap cleanup EXIT

git -C "$REPO_ROOT" archive --format=tar "$RELEASE_SHA" \
  skills/earn/lancers/scripts/application_loop.py \
  skills/earn/lancers/scripts/application_tick.py \
  skills/earn/lancers/scripts/status.py \
  skills/earn/lancers/scripts/lancers_adapter.py \
  skills/_shared/marketplace-core/scripts/application_transaction.py \
  skills/_shared/marketplace-core/scripts/contracts.py \
  skills/_shared/marketplace-core/scripts/ledger.py \
  skills/_shared/marketplace-core/schemas/event.schema.json \
  skills/_shared/marketplace-core/schemas/opportunity.schema.json \
  skills/gig-work/schemas/application_decisions.schema.json \
  runtime/agent-runner/agent_runner.py \
  runtime/agent-runner/token_budget.py \
  runtime/agent-runner/config.json | tar -xf - -C "$STAGING"
mkdir -p "$STAGING/skills/agent-runner"
for source in agent_runner.py token_budget.py config.json; do
  mv "$STAGING/runtime/agent-runner/$source" "$STAGING/skills/agent-runner/$source"
done
rmdir "$STAGING/runtime/agent-runner" "$STAGING/runtime"
chmod 755 "$STAGING/skills/agent-runner/agent_runner.py"

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

INSTALLED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
"$PYTHON_BIN" - "$STATE_ROOT/deployment.json" "$RELEASE_PATH" "$RELEASE_SHA" \
  "$INSTALL_MODE" "$INSTALLED_AT" "$LABEL" <<'PY'
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

manifest_path, release_path, deployed_sha, mode, installed_at, label = sys.argv[1:]
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
