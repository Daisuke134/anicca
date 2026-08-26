#!/usr/bin/env bash
# Life Manager install — bootstraps the Life Manager automaton body into a runtime root on
# the user's always-on machine. Idempotent: safe to re-run. Self-host / OSS path.
#
# Registry-driven: every capability lives as a SLOT in skills/registry.json
# (the SSOT). This script reads that registry and syncs each declared/live slot
# into $ANICCA_HOME/skills/<slot>/ — so adding a capability is "drop a dir +
# declare a slot", never "edit install.sh". (Foundation collision-prevention.)
#
# What this does:
#   1. Verify system deps (git, jq, node, npm, python3, rsync)
#   2. Install frozen repository dependencies from lockfiles
#   3. Scaffold the runtime root ($LIFE_MANAGER_HOME) + .env (never overwrite)
#   4. Sync skills/_shared and EVERY declared slot into the runtime body
#   5. Optionally register the host daemon
#   6. Print "what's next" (fuel key + first wake)
#
# What this does NOT do:
#   - Ask for API keys / private keys (handled out of band — see .env.example)
#   - Broadcast any on-chain tx or start earning (the automaton loop does that)
#   - Touch anything outside $LIFE_MANAGER_HOME when daemon registration is disabled

set -euo pipefail
trap 'echo "[install] FAILED on line $LINENO. nothing destructive — re-run is safe."' ERR

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$#" -gt 0 ]; then
  case "$1" in
    coconala)
      shift
      exec bash "$REPO_ROOT/skills/earn/gig/install.sh" "$@"
      ;;
    job-hunter)
      shift
      exec zsh "$REPO_ROOT/apps/job-search-loop/scripts/install-oss.sh" "$@"
      ;;
    agent-economy)
      shift
      LIFE_MANAGER_AGENT_ECONOMY=1
      export LIFE_MANAGER_AGENT_ECONOMY
      exec bash "$REPO_ROOT/install.sh" "$@"
      ;;
    *)
      echo "[install] unknown product '$1'; supported: coconala, job-hunter, agent-economy" >&2
      exit 2
      ;;
  esac
fi
LIFE_MANAGER_AGENT_ECONOMY="${LIFE_MANAGER_AGENT_ECONOMY:-0}"
if [ "${ANICCA_INSTANCE:-}" = "agent-economy" ]; then
  LIFE_MANAGER_AGENT_ECONOMY=1
fi
if [ "${LIFE_MANAGER_RELEASE_ROOT+x}" = "x" ] && [ "$(basename "$LIFE_MANAGER_RELEASE_ROOT")" = "life-manager" ]; then
  LIFE_MANAGER_AGENT_ECONOMY=1
fi
case "$LIFE_MANAGER_AGENT_ECONOMY" in 0|1) ;; *)
  echo "[install] LIFE_MANAGER_AGENT_ECONOMY must be 0 or 1" >&2
  exit 2
esac
LIFE_MANAGER_RELEASE_ROOT="${LIFE_MANAGER_RELEASE_ROOT:-$HOME/loops/life-manager}"
if [ "$LIFE_MANAGER_AGENT_ECONOMY" = "1" ]; then
  LIFE_MANAGER_HOME="${LIFE_MANAGER_HOME:-${ANICCA_HOME:-$HOME/loops/agent-economy}}"
else
  LIFE_MANAGER_HOME="${LIFE_MANAGER_HOME:-${ANICCA_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/life-manager}}"
fi
ANICCA_HOME="$LIFE_MANAGER_HOME"
export LIFE_MANAGER_HOME ANICCA_HOME
LIFE_MANAGER_INSTALL_DAEMON="${LIFE_MANAGER_INSTALL_DAEMON:-1}"
LIFE_MANAGER_INSTALL_DEPS="${LIFE_MANAGER_INSTALL_DEPS:-1}"
LIFE_MANAGER_DEPS_ROOT="${LIFE_MANAGER_DEPS_ROOT:-$HOME/loops/.life-manager-deps}"
REGISTRY="$REPO_ROOT/skills/registry.json"

validate_agent_economy_release() {
  local release_root="$1"
  python3 - "$release_root" <<'PY'
import json
import hashlib
import os
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1]).expanduser()
if root.name != "life-manager":
    raise SystemExit("agent-economy release root must be namespaced as life-manager")
root = Path(os.path.realpath(root))
current = root / "current"
if not current.is_symlink():
    raise SystemExit(f"agent-economy current pointer is missing: {current}")
try:
    release = Path(os.path.realpath(current))
except OSError as error:
    raise SystemExit("agent-economy current target cannot be resolved") from error
releases = root / "releases"
if not releases.is_dir():
    raise SystemExit(f"agent-economy releases root is missing: {releases}")
releases = Path(os.path.realpath(releases))
if release.parent != releases:
    raise SystemExit("agent-economy current escapes the namespaced releases root")
metadata_path = release / "RELEASE.json"
if metadata_path.is_symlink() or not metadata_path.is_file():
    raise SystemExit(f"agent-economy release metadata is missing: {metadata_path}")
try:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
except (OSError, ValueError) as error:
    raise SystemExit("agent-economy release metadata is invalid") from error
if not isinstance(metadata, dict):
    raise SystemExit("agent-economy release metadata must be an object")
if metadata.get("namespace") != "life-manager":
    raise SystemExit("agent-economy release metadata namespace is invalid")
if Path(os.path.realpath(str(metadata.get("release_root", "")))) != root:
    raise SystemExit("agent-economy release metadata root does not match current")
if metadata.get("current") and Path(os.path.realpath(str(metadata["current"]))) != Path(os.path.realpath(str(current))):
    raise SystemExit("agent-economy release metadata current does not match current")
release_id = str(metadata.get("release_id", ""))
sha = str(metadata.get("sha", ""))
if release_id != release.name or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
    raise SystemExit("agent-economy release metadata identity is invalid")
if metadata.get("git_commit") != sha:
    raise SystemExit("agent-economy release metadata commit is invalid")
manifest_path = release / "SOURCE-MANIFEST.json"
if manifest_path.is_symlink() or not manifest_path.is_file():
    raise SystemExit("agent-economy source manifest is missing")
raw_manifest = manifest_path.read_bytes()
entries = []
release_real = Path(os.path.realpath(release))
for path in sorted(release.rglob("*")):
    relative = path.relative_to(release).as_posix()
    if relative in {"RELEASE.json", "SOURCE-MANIFEST.json", "DEPENDENCY-MANIFEST.tsv"} or relative.startswith("node_modules/"):
        continue
    item = path.lstat()
    if stat.S_ISREG(item.st_mode):
        entries.append({"path": relative, "mode": format(stat.S_IMODE(item.st_mode) & 0o555, "04o"), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    elif stat.S_ISLNK(item.st_mode):
        target = os.readlink(path)
        target_real = Path(os.path.realpath(path))
        if target_real != release_real and release_real not in target_real.parents:
            raise SystemExit("agent-economy source symlink escapes release")
        entries.append({"path": relative, "mode": format(stat.S_IMODE(item.st_mode) & 0o555, "04o"), "sha256": hashlib.sha256(target.encode()).hexdigest(), "target": target})
expected_manifest = (json.dumps({"version": 1, "entries": entries}, sort_keys=True, separators=(",", ":")) + "\n").encode()
if raw_manifest != expected_manifest or hashlib.sha256(raw_manifest).hexdigest() != str(metadata.get("source_manifest_sha256", "")):
    raise SystemExit("agent-economy source manifest does not match release")
dependency_manifest_path = release / "DEPENDENCY-MANIFEST.tsv"
node_modules = release / "node_modules"
if dependency_manifest_path.is_symlink() or not dependency_manifest_path.is_file():
    raise SystemExit("agent-economy dependency manifest is missing")
if node_modules.is_symlink() or not node_modules.is_dir():
    raise SystemExit("agent-economy release node_modules is missing")
node_modules_real = Path(os.path.realpath(node_modules))
dependency_lines = []
for path in sorted(node_modules.rglob("*"), key=lambda item: item.relative_to(release).as_posix()):
    relative = path.relative_to(release).as_posix()
    item = path.lstat()
    if stat.S_ISREG(item.st_mode):
        dependency_lines.append(f"file\t{relative}\t{format(stat.S_IMODE(item.st_mode) & 0o555, 'o')}\t{hashlib.sha256(path.read_bytes()).hexdigest()}\t-")
    elif stat.S_ISLNK(item.st_mode):
        target = Path(os.path.realpath(path))
        if target != node_modules_real and node_modules_real not in target.parents:
            raise SystemExit("agent-economy dependency symlink escapes node_modules")
        dependency_lines.append(f"symlink\t{relative}\t{format(stat.S_IMODE(item.st_mode) & 0o555, 'o')}\t-\t{os.readlink(path)}")
expected_dependencies = ("\n".join(dependency_lines) + ("\n" if dependency_lines else "")).encode()
raw_dependencies = dependency_manifest_path.read_bytes()
if raw_dependencies != expected_dependencies or hashlib.sha256(raw_dependencies).hexdigest() != str(metadata.get("dependency_tree_manifest_sha256", "")):
    raise SystemExit("agent-economy dependency manifest does not match release")
if release.name != sha and not release.name.endswith("-" + sha[:8]):
    raise SystemExit("agent-economy release metadata sha does not match release")
for path in [release, *release.rglob("*")]:
    if path.is_symlink():
        continue
    if path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        raise SystemExit(f"agent-economy release is writable: {path}")
print(f"{release}\t{release_id}\t{sha}")
PY
}

case "$LIFE_MANAGER_INSTALL_DAEMON" in 0|1) ;; *)
  echo "[install] LIFE_MANAGER_INSTALL_DAEMON must be 0 or 1" >&2
  exit 2
esac
case "$LIFE_MANAGER_INSTALL_DEPS" in 0|1) ;; *)
  echo "[install] LIFE_MANAGER_INSTALL_DEPS must be 0 or 1" >&2
  exit 2
esac

cyan(){ printf "\033[36m%s\033[0m\n" "$*"; }
green(){ printf "\033[32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$*"; }
red(){ printf "\033[31m%s\033[0m\n" "$*"; }

cyan "================================================================"
cyan "  Life Manager install — self-host automaton body"
cyan "  Repo root  : $REPO_ROOT"
cyan "  Runtime    : $LIFE_MANAGER_HOME"
cyan "  Registry   : $REGISTRY"
cyan "================================================================"
echo

# ─── 1. system deps ────────────────────────────────────────────────────
cyan "[1/6] checking system deps…"
for bin in git jq node npm python3 rsync; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    red "  ✗ $bin missing — install it first then re-run."
    exit 2
  fi
  green "  ✓ $bin"
done
echo

if [ "$LIFE_MANAGER_AGENT_ECONOMY" = "1" ]; then
  RELEASE_READBACK="$(validate_agent_economy_release "$LIFE_MANAGER_RELEASE_ROOT")" \
    || { red "  ✗ agent-economy current is not a sealed namespaced release"; exit 2; }
  IFS=$'\t' read -r RELEASE_SOURCE RELEASE_ID RELEASE_SHA <<EOF
$RELEASE_READBACK
EOF
  # All code and manifests for this installation are read from the immutable release. The source
  # checkout remains authoring-only and is never copied into the agent-economy runtime owner.
  REPO_ROOT="$RELEASE_SOURCE"
  REGISTRY="$REPO_ROOT/skills/registry.json"
  export REPO_ROOT LIFE_MANAGER_RELEASE_ROOT ANICCA_REPO="$RELEASE_SOURCE" ANICCA_CODE_ROOT="$RELEASE_SOURCE" \
    ANICCA_RELEASE_ID="$RELEASE_ID" ANICCA_RELEASE_SHA="$RELEASE_SHA"
  green "  ✓ sealed release $RELEASE_ID  ($RELEASE_SOURCE)"
fi

# ─── 2. frozen dependencies ────────────────────────────────────────────
cyan "[2/6] installing frozen dependencies…"
if [ "$LIFE_MANAGER_INSTALL_DEPS" = "1" ]; then
  if [ "$LIFE_MANAGER_AGENT_ECONOMY" = "1" ]; then
    # cut-loop-release already installed the lockfile-frozen dependencies inside this sealed release.
    # Never mutate it or create a shared ~/loops/node_modules link during a pinned install.
    green "  ✓ sealed release dependencies reused (npm install/link skipped)"
  elif [ -w "$REPO_ROOT" ] && [ -f "$REPO_ROOT/package-lock.json" ]; then
    (cd "$REPO_ROOT" && npm ci --no-audit --no-fund)
    (cd "$REPO_ROOT/apps/life-manager" && npm ci --no-audit --no-fund)
    mkdir -p "$HOME/loops"
    ln -sfn "$REPO_ROOT/node_modules" "$HOME/loops/node_modules"
    green "  ✓ root + apps/life-manager npm lockfiles installed"
  else
    # Immutable cut-loop releases cannot receive node_modules. Install the exact root lockfile into
    # a writable durable dependency root, then expose it through the release-parent lookup path so
    # ESM package imports from any ~/loops/releases/<sha> resolve without mutating the release.
    mkdir -p "$LIFE_MANAGER_DEPS_ROOT"
    cp "$REPO_ROOT/package.json" "$LIFE_MANAGER_DEPS_ROOT/package.json"
    cp "$REPO_ROOT/package-lock.json" "$LIFE_MANAGER_DEPS_ROOT/package-lock.json"
    (cd "$LIFE_MANAGER_DEPS_ROOT" && npm ci --no-audit --no-fund --ignore-scripts)
    mkdir -p "$HOME/loops"
    ln -sfn "$LIFE_MANAGER_DEPS_ROOT/node_modules" "$HOME/loops/node_modules"
    green "  ✓ immutable-release dependencies installed at $LIFE_MANAGER_DEPS_ROOT"
  fi
else
  yellow "  • dependency install disabled by LIFE_MANAGER_INSTALL_DEPS=0"
fi
echo

restore_agent_economy_state_ancestors() {
  local release_real path path_real
  release_real="$(cd "$LIFE_MANAGER_RELEASE_ROOT" 2>/dev/null && pwd -P)" \
    || { red "  ✗ namespaced release root cannot be resolved"; return 2; }
  # Existing runtime directories may have been sealed by an earlier installer. Restore only the
  # owner rwx bits needed for mutable state descendants; never chmod the sealed release or any
  # unrelated runtime tree.
  for path in \
    "$ANICCA_HOME" \
    "$ANICCA_HOME/skills" \
    "$ANICCA_HOME/skills/agent-economy" \
    "$ANICCA_HOME/skills/earn" \
    "$ANICCA_HOME/skills/earn/x402-sell" \
    "$ANICCA_HOME/skills/cook"; do
    [ -e "$path" ] || continue
    [ -d "$path" ] || { red "  ✗ required state ancestor is not a directory: $path"; return 2; }
    path_real="$(cd "$path" 2>/dev/null && pwd -P)" \
      || { red "  ✗ required state ancestor cannot be resolved: $path"; return 2; }
    case "$path_real" in
      "$release_real"|"$release_real"/*)
        red "  ✗ refusing to chmod sealed release through runtime state path: $path"
        return 2
        ;;
    esac
    chmod u+rwx "$path"
  done
}

# ─── 3. runtime root + env ─────────────────────────────────────────────
cyan "[3/6] preparing runtime root…"
mkdir -p "$ANICCA_HOME"/{skills,state,identity,logs}
green "  ✓ $ANICCA_HOME"

if [ ! -f "$ANICCA_HOME/.env" ]; then
  if [ -f "$REPO_ROOT/.env.example" ]; then
    cp "$REPO_ROOT/.env.example" "$ANICCA_HOME/.env"
  else
    : > "$ANICCA_HOME/.env"
  fi
  chmod 600 "$ANICCA_HOME/.env"
  yellow "  ✎ created $ANICCA_HOME/.env — fill in 1 fuel key + wallet before first wake."
else
  green "  ✓ $ANICCA_HOME/.env  (preserved)"
fi

# default genesis prompt — the loop needs an instruction to act on each wake.
# Canonical hustle genesis lives at identity/genesis.md in the repo; ship it verbatim.
if [ ! -f "$ANICCA_HOME/identity/genesis.md" ]; then
  if [ -f "$REPO_ROOT/identity/genesis.md" ]; then
    cp "$REPO_ROOT/identity/genesis.md" "$ANICCA_HOME/identity/genesis.md"
  else
    cat > "$ANICCA_HOME/identity/genesis.md" <<'GENESIS'
You are Life Manager — a self-funding agent. Every wake costs USDC; idle time is death. Your one job
every waking moment is to EARN — grow your USDC net worth with no human in the loop. You always
have a job: deploy idle USDC into the best safe stable yield (Aave / Beefy / Morpho). Do not rest
long until your net worth rises. Use a frontier model (a free model cannot earn). call run_skill
slot "earn" each wake; keep an honest ledger.
GENESIS
  fi
  green "  ✓ $ANICCA_HOME/identity/genesis.md  (hustle genesis)"
else
  green "  ✓ $ANICCA_HOME/identity/genesis.md  (preserved)"
fi
echo

# ─── 4. shared lib ─────────────────────────────────────────────────────
cyan "[4/6] syncing _shared lib…"
if [ "$LIFE_MANAGER_AGENT_ECONOMY" = "1" ]; then
  restore_agent_economy_state_ancestors
  # Agent-economy code stays in the sealed release. Create only the mutable state namespace; do not
  # copy executable skills into it, because launchd and run-skill resolve code from ANICCA_CODE_ROOT.
  mkdir -p "$ANICCA_HOME/skills/agent-economy/state" "$ANICCA_HOME/skills/earn/state" \
    "$ANICCA_HOME/skills/cook/state" "$ANICCA_HOME/skills/earn/x402-sell/state"
  green "  ✓ release-backed agent-economy state roots prepared (code sync skipped)"
elif [ -d "$REPO_ROOT/skills/_shared" ]; then
  mkdir -p "$ANICCA_HOME/skills/_shared"
  rsync -a --delete --exclude='state/' --exclude='__pycache__/' \
    "$REPO_ROOT/skills/_shared/" "$ANICCA_HOME/skills/_shared/"
  green "  ✓ _shared synced"
else
  yellow "  ⚠ skills/_shared not in repo — skipping."
fi
echo

# ─── 4.1. registry-driven slot sync ────────────────────────────────────
cyan "[4.1/6] syncing skills from registry…"
if [ "$LIFE_MANAGER_AGENT_ECONOMY" = "1" ]; then
  green "  ✓ release-backed agent-economy install does not copy executable skills"
else
  if [ ! -f "$REGISTRY" ]; then
    red "  ✗ registry not found at $REGISTRY — cannot sync slots."
    exit 3
  fi
  # iterate over every slot key; sync its dir; report status. Foundation pre-declares
  # all slots, so every builder's capability gets installed the moment its files land.
  SLOT_KEYS=$(jq -r '.slots | keys[]' "$REGISTRY")
  SYNCED=0; DECLARED_ONLY=0
  while IFS= read -r slot; do
    [ -z "$slot" ] && continue
    dir=$(jq -r --arg k "$slot" '.slots[$k].dir' "$REGISTRY")
    status=$(jq -r --arg k "$slot" '.slots[$k].status' "$REGISTRY")
    entry=$(jq -r --arg k "$slot" '.slots[$k].entrypoint' "$REGISTRY")
    src="$REPO_ROOT/$dir"
    dst="$ANICCA_HOME/$dir"
    if [ ! -d "$src" ]; then
      yellow "  ⚠ $slot — dir $dir missing in repo, skip"
      continue
    fi
    mkdir -p "$dst"
    rsync -a --delete --exclude='state/' --exclude='__pycache__/' "$src/" "$dst/"
    # Immutable releases are intentionally chmod a-w. Runtime state is outside the release but lives
    # below each synced slot; restore only this destination root's owner write/execute bits before
    # creating its state directory. Never make the release writable.
    chmod u+rwx "$dst"
    mkdir -p "$dst/state"
    if [ "$status" = "live" ]; then
      green "  ✓ $slot  [live]  -> $dir/$entry"
      SYNCED=$((SYNCED+1))
    else
      yellow "  • $slot  [$status]  (reserved, entrypoint $entry pending)"
      DECLARED_ONLY=$((DECLARED_ONLY+1))
    fi
  done <<< "$SLOT_KEYS"
  echo
  green "  synced $SYNCED live slot(s), $DECLARED_ONLY reserved slot(s)."
  echo
fi

# ─── 5. supervised, self-updating daemon (optional host mutation) ──────
cyan "[5/6] daemon registration…"
if [ "$LIFE_MANAGER_INSTALL_DAEMON" = "1" ]; then
  chmod +x "$REPO_ROOT/runtime/anicca-daemon.sh" 2>/dev/null || true
  if [ "$(uname)" = "Darwin" ]; then
    PLIST="$HOME/Library/LaunchAgents/com.anicca.daemon.plist"
    mkdir -p "$HOME/Library/LaunchAgents"
    sed -e "s#__REPO__#$REPO_ROOT#g" -e "s#__ANICCA_HOME__#$ANICCA_HOME#g" -e "s#__HOME__#$HOME#g" \
      "$REPO_ROOT/runtime/com.anicca.daemon.plist.template" > "$PLIST"
    launchctl unload "$PLIST" 2>/dev/null || true
    if launchctl load -w "$PLIST" 2>/dev/null; then
      green "  ✓ launchd daemon loaded (com.anicca.daemon)"
    else
      cyan "  ! launchctl load failed; load it yourself: launchctl load -w $PLIST"
    fi
  else
    green "  Linux/cloud: run runtime/anicca-daemon.sh under systemd or Docker restart=always."
  fi
else
  green "  ✓ disabled (LIFE_MANAGER_INSTALL_DAEMON=0); no LaunchAgent/system service changed"
fi
echo

# ─── 6. summary ────────────────────────────────────────────────────────
cyan "[6/6] done."
echo
green "What's next:"
cat <<EOM
  DEFAULT = FULLY LOCAL + FREE. No server key, no API key required. Life Manager pays
  its OWN compute via ClawRouter/BlockRun (USDC x402) from its OWN wallet — like
  Franklin. You provide only this device (shelter); Life Manager buys its own food.

  1. Start the self-pay proxy + the Life Manager loop (one command, from the repo root):
       cd "$REPO_ROOT/runtime/compute-proxy" && npm install && cd "$REPO_ROOT"  # one-time
       ./start-local.sh node runtime/loop/index.mjs
     This starts the self-pay compute proxy on http://127.0.0.1:8402/v1 (signs
     every inference in USDC from a self-owned wallet; empty wallet ⇒ free model,
     \$0) AND the Life Manager loop (runtime/loop/) which, each wake, asks ClawRouter's
     'auto' router, runs a tool (e.g. the earn skill), and appends to
     $ANICCA_HOME/state/ledger.jsonl. The report slot POSTs signed telemetry to
     https://aniccaai.com so you show on /dashboard.
  2. (OPTIONAL) Unlock frontier models / more earning: send USDC to the wallet
     address printed at startup — the loop then lets ClawRouter pick a paid model.
     Or set ANICCA_BRAIN=claude-p to drive the loop with Claude Code instead.
  4. (OPTIONAL) Life Manager keys: GEMINI_API_KEY, TWILIO_*, GOOGLE_API_KEY,
     AGENTMAIL_API_KEY — only for phone wake-calls / lateness alerts.

  # FUTURE (cloud, not active): once Conway is available, the same body can run
  # on a droplet where Life Manager ALSO pays its own server cost — see README "Cloud".

  Slots are declared in skills/registry.json. To enable a reserved slot, drop its
  implementation into its dir and flip status to "live" — no install.sh edit.

  Repo: https://github.com/Daisuke134/life-manager
EOM
echo
green "Life Manager install complete."
