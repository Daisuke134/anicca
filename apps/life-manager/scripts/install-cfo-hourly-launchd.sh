#!/usr/bin/env bash
set -euo pipefail

# Stage the reviewed closure into a durable user-owned release, then render the one launchd plist
# against that stable path. This installer deliberately does not bootstrap/bootout launchd.
UID_VALUE="${1:-${LM_CFO_UID:-}}"
CHAT_ID="${2:-${LM_CFO_TELEGRAM_CHAT_ID:-}}"
if [[ ! "$UID_VALUE" =~ ^[A-Za-z0-9_-]{1,128}$ ]]; then
  echo "usage: install-cfo-hourly-launchd.sh <owner-uid> <telegram-chat-id>" >&2
  exit 2
fi
if [[ ! "$CHAT_ID" =~ ^-?[0-9]{1,32}$ ]]; then
  echo "telegram chat id must be numeric" >&2
  exit 2
fi

HOME_DIR="${HOME:?HOME is required}"
CODEX_HOME_VALUE="${CODEX_HOME:-$HOME_DIR/.codex}"
DOMAIN="gui/$(id -u)"
SOURCE_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOOP_TOML="$SOURCE_REPO_ROOT/loops/cfo-hourly/loop.toml"
PYTHON_BIN=/opt/homebrew/bin/python3
[[ -x "$PYTHON_BIN" ]] || PYTHON_BIN=python3

if [[ ! -f "$LOOP_TOML" ]]; then
  echo "canonical CFO loop declaration is missing" >&2
  exit 1
fi
LOOP_SPEC="$($PYTHON_BIN - "$LOOP_TOML" <<'PY'
import sys
import tomllib

path = sys.argv[1]
try:
    with open(path, "rb") as handle:
        loop = tomllib.load(handle)
except Exception as exc:
    print(f"invalid CFO loop declaration: {exc}", file=sys.stderr)
    raise SystemExit(1)

if loop.get("name") != "cfo-hourly":
    print("CFO loop declaration name must be cfo-hourly", file=sys.stderr)
    raise SystemExit(1)
job = (loop.get("jobs") or {}).get("hourly")
if not isinstance(job, dict):
    print("CFO loop declaration must define jobs.hourly", file=sys.stderr)
    raise SystemExit(1)
label, program, interval = job.get("label"), job.get("program"), job.get("interval_seconds")
if not isinstance(label, str) or not label or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-" for char in label):
    print("CFO hourly job label is invalid", file=sys.stderr)
    raise SystemExit(1)
if not isinstance(program, str) or not program or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._/-" for char in program) or program.startswith("/") or ".." in program.split("/"):
    print("CFO hourly job program must be a relative path without '..'", file=sys.stderr)
    raise SystemExit(1)
if not isinstance(interval, int) or isinstance(interval, bool) or interval <= 0:
    print("CFO hourly interval_seconds must be a positive integer", file=sys.stderr)
    raise SystemExit(1)
print(f"{label}\t{program}\t{interval}")
PY
)"
IFS=$'\t' read -r CFO_LABEL CFO_PROGRAM CFO_INTERVAL <<<"$LOOP_SPEC"
RELEASE_ROOT="${LIFE_MANAGER_CFO_RELEASE_ROOT:-$HOME_DIR/.local/share/life-manager/cfo-hourly}"
RELEASES_DIR="$RELEASE_ROOT/releases"
CURRENT_LINK="$RELEASE_ROOT/current"
ENV_FILE="${LIFE_MANAGER_ENV_FILE:-$HOME_DIR/.local/state/life-manager/.env}"
STATE_DIR="${CFO_STATE_DIR:-$HOME_DIR/loops/cfo-hourly}"
TEMPLATE="$SOURCE_REPO_ROOT/apps/life-manager/launchd/ai.anicca.life-manager-cfo-hourly.plist.template"
TARGET="$HOME_DIR/Library/LaunchAgents/$CFO_LABEL.plist"

if [[ ! -f "$TEMPLATE" || ! -f "$SOURCE_REPO_ROOT/apps/life-manager/scripts/cfo-hourly-local.js" ||
      ! -f "$SOURCE_REPO_ROOT/$CFO_PROGRAM" ]]; then
  echo "repository-owned CFO runtime is missing" >&2
  exit 1
fi

RELEASE_ID="$(date +%Y%m%dT%H%M%S)-$$"
mkdir -p "$RELEASES_DIR" "$HOME_DIR/Library/LaunchAgents" "$STATE_DIR"
STAGE="$(mktemp -d "$RELEASES_DIR/.stage.XXXXXX")"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

copy_file() {
  local relative="$1" source="$SOURCE_REPO_ROOT/$1" destination="$STAGE/$1"
  [[ -f "$source" ]] || { echo "missing runtime file: $relative" >&2; exit 1; }
  mkdir -p "$(dirname "$destination")"
  install -m 600 "$source" "$destination"
}

# Keep the staged release narrow: the hourly entrypoints, their transitive CFO closure, canonical
# shared owners, and the lockfile manifest used to install the one runtime dependency.
copy_file apps/life-manager/scripts/cfo-hourly-local.js
copy_file apps/life-manager/scripts/cfo-moneytree-codex-read.js
for file in \
  cfo-anthropic-receipt-local-source.js cfo-daily-run.js cfo-daily-snapshot.js cfo-financial-source.js \
  cfo-google-invoice-local-source.js cfo-local-agent-capture-reconciliation.js cfo-local-agent-usage-attribution.js \
  cfo-local-agent-usage-batch-store.js cfo-local-agent-usage-chain.js cfo-local-agent-usage-collector.js \
  cfo-local-agent-usage-cursor.js cfo-local-agent-usage-runner.js cfo-moneytree-recovery.js cfo-moneytree-state.js \
  cfo-moneytree.js cfo-moneytree-refresh.js cfo-provider-billing-reconciliation.js cfo-recovery-snapshot.js cfo-registry.js cfo-supabase-rpc.js \
  cfo-telegram-callback.js cfo-telegram-delivery.js cfo-telegram-send.js cfo-telegram.js ledger.js telegram.js i18n.js; do
  copy_file "apps/life-manager/lib/$file"
done
copy_file apps/life-manager/lib/transport/mail-gog.js
copy_file apps/life-manager/package.json
copy_file apps/life-manager/package-lock.json
for file in ceo_budget.py registry-enforce.sh registry_enforce_read.py registry_write_gate.py; do
  copy_file "lib/$file"
done
for file in budget-check.sh budget_check_cli.py; do
  copy_file "bin/$file"
done
for file in record-cost-event.sh record_cost_event.py; do
  copy_file "bin/$file"
done
copy_file config/loop-registry.json
copy_file config/ceo-budget-config.json
copy_file skills/cfo/SKILL.md
copy_file "$CFO_PROGRAM"

chmod 700 "$STAGE/$CFO_PROGRAM" "$STAGE/bin/budget-check.sh" "$STAGE/bin/record-cost-event.sh" "$STAGE/lib/registry-enforce.sh"

verify_dependency_manifest() {
  APP_DIR="$STAGE/apps/life-manager" node - <<'NODE'
const fs = require("node:fs");
const path = process.env.APP_DIR;
const pkg = JSON.parse(fs.readFileSync(`${path}/package.json`, "utf8"));
const lock = JSON.parse(fs.readFileSync(`${path}/package-lock.json`, "utf8"));
const declared = pkg.dependencies || {};
const locked = lock.packages?.[""]?.dependencies || {};
const mismatches = Object.entries(declared)
  .filter(([name, range]) => locked[name] !== range)
  .map(([name, range]) => `${name} (package.json=${range}, lock=${locked[name] ?? "missing"})`);
if (mismatches.length > 0) {
  console.error(`package-lock dependency mismatch: ${mismatches.join(", ")}`);
  process.exit(1);
}
NODE
}

verify_staged_dependencies() {
  APP_DIR="$STAGE/apps/life-manager" node - <<'NODE'
const fs = require("node:fs");
const pathModule = require("node:path");
const path = fs.realpathSync(process.env.APP_DIR);
const pkg = JSON.parse(fs.readFileSync(`${path}/package.json`, "utf8"));
const lock = JSON.parse(fs.readFileSync(`${path}/package-lock.json`, "utf8"));
const lockPackages = lock.packages || {};
const missing = [];
const mismatched = [];
const packageMetadata = (name) => {
  let resolved;
  try {
    resolved = require.resolve(name, { paths: [path] });
  } catch (_) {
    return null;
  }
  let cursor = pathModule.dirname(resolved);
  while (cursor.startsWith(path) && cursor !== pathModule.dirname(cursor)) {
    const candidate = pathModule.join(cursor, "package.json");
    if (fs.existsSync(candidate)) {
      const metadata = JSON.parse(fs.readFileSync(candidate, "utf8"));
      if (metadata.name === name) return metadata;
    }
    cursor = pathModule.dirname(cursor);
  }
  return null;
};
for (const name of Object.keys(pkg.dependencies || {})) {
  const metadata = packageMetadata(name);
  const locked = lockPackages[`node_modules/${name}`];
  if (!metadata || !locked || typeof locked.version !== "string") {
    missing.push(name);
    continue;
  }
  if (metadata.version !== locked.version) {
    mismatched.push(`${name} (staged=${metadata.version ?? "missing"}, lock=${locked.version})`);
  }
}
if (missing.length > 0) {
  console.error(`required staged dependencies missing: ${missing.join(", ")}`);
  process.exit(1);
}
if (mismatched.length > 0) {
  console.error(`required staged dependency versions differ from lock: ${mismatched.join(", ")}`);
  process.exit(1);
}
NODE
}

verify_dependency_manifest
NODE_MODULES_SOURCE="${LIFE_MANAGER_CFO_NODE_MODULES_SOURCE:-}"
if [[ -n "$NODE_MODULES_SOURCE" && -d "$NODE_MODULES_SOURCE" ]]; then
  NODE_MODULES_SOURCE="$(cd "$NODE_MODULES_SOURCE" && pwd -P)"
  mkdir -p "$STAGE/apps/life-manager/node_modules"
  cp -aL "$NODE_MODULES_SOURCE"/. "$STAGE/apps/life-manager/node_modules/"
  if find "$STAGE/apps/life-manager/node_modules" -type l -print -quit | grep -q .; then
    echo "offline node_modules copy contains a symlink" >&2
    exit 1
  fi
  verify_staged_dependencies
else
  if [[ -n "$NODE_MODULES_SOURCE" ]]; then
    echo "LIFE_MANAGER_CFO_NODE_MODULES_SOURCE is not a directory; falling back to npm ci" >&2
  fi
  (cd "$STAGE/apps/life-manager" && npm ci --omit=dev --ignore-scripts --no-audit --no-fund >/dev/null)
  verify_staged_dependencies
fi

initialize_durable_config() {
  local relative="$1" source="$SOURCE_REPO_ROOT/$1" target="$STATE_DIR/$1"
  [[ -f "$source" ]] || { echo "missing durable config source: $relative" >&2; exit 1; }
  if [[ ! -e "$target" && ! -L "$target" ]]; then
    mkdir -p "$(dirname "$target")"
    install -m 600 "$source" "$target"
  fi
}

# Registry and budget state belongs outside releases. Seed each file once; a reinstall must not
# overwrite an operator's paused allocation or any other durable registry decision.
initialize_durable_config config/loop-registry.json
initialize_durable_config config/ceo-budget-config.json

mkdir -p "$STAGE/apps/life-manager/launchd"
install -m 600 "$TEMPLATE" "$STAGE/apps/life-manager/launchd/ai.anicca.life-manager-cfo-hourly.plist.template"
mv "$STAGE" "$RELEASES_DIR/$RELEASE_ID"
STAGE=""
LINK_TEMP="$RELEASE_ROOT/.current.$$.tmp"
ln -s "$RELEASES_DIR/$RELEASE_ID" "$LINK_TEMP"
mv -fh "$LINK_TEMP" "$CURRENT_LINK"

TMP_PLIST="$(mktemp "${TMPDIR:-/tmp}/life-manager-cfo-hourly.XXXXXX")"
trap 'rm -f "$TMP_PLIST"' EXIT
sed \
  -e "s|__CANONICAL_REPO_ROOT__|$CURRENT_LINK|g" \
  -e "s|__CANONICAL_APP_DIR__|$CURRENT_LINK/apps/life-manager|g" \
  -e "s|__CFO_LABEL__|$CFO_LABEL|g" \
  -e "s|__CFO_PROGRAM__|$CFO_PROGRAM|g" \
  -e "s|__CFO_ENV_FILE__|$ENV_FILE|g" \
  -e "s|__CFO_STATE_DIR__|$STATE_DIR|g" \
  -e "s|__CFO_UID__|$UID_VALUE|g" \
  -e "s|__CFO_CHAT_ID__|$CHAT_ID|g" \
  -e "s|__HOME__|$HOME_DIR|g" \
  -e "s|__CODEX_HOME__|$CODEX_HOME_VALUE|g" \
  "$TEMPLATE" >"$TMP_PLIST"
/usr/bin/plutil -replace StartInterval -integer "$CFO_INTERVAL" "$TMP_PLIST"
/usr/bin/plutil -lint "$TMP_PLIST"
/usr/bin/install -m 600 "$TMP_PLIST" "$TARGET"

# Refresh the loaded job as well as the on-disk plist. Without bootout/bootstrap,
# launchd keeps the previous definition (and can continue executing an old worktree).
SERVICE="$DOMAIN/$CFO_LABEL"
launchctl bootout "$SERVICE" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$TARGET"
launchctl enable "$SERVICE"
launchctl kickstart -k "$SERVICE"
launchctl print "$SERVICE" >/dev/null
echo "$TARGET"
echo "$CURRENT_LINK/apps/life-manager"
